# -*- coding: utf-8 -*-
import time
import traceback

import arcpy


GROUP_TYPES = ("Height", "Velocity", "Depth")
PARCEL_ID_FIELD_CANDIDATES = ("PARCEL_PFI", "PROPERTY_PFI", "PROP_PFI", "PFI", "OBJECTID")
PARCEL_SPI_FIELD_CANDIDATES = ("PARCEL_SPI", "PROPERTY_SPI", "PROP_SPI", "SPI")
ZONE_LAYER_NAME = "eps_selected_zone"


class Toolbox:
    def __init__(self):
        self.label = "EPS"
        self.alias = "eps"
        self.tools = [ExtractParcelStats]


class ExtractParcelStats:
    def __init__(self):
        self.label = "Extract Parcel Stats"
        self.description = (
            "For each selected parcel, prints MIN and MAX values to the geoprocessing messages, "
            "aggregated across all visible rasters inside the chosen Height, Velocity, and Depth "
            "group layers. Honours ancestor group visibility (a raster is excluded if any parent "
            "group is unchecked)."
        )

    def getParameterInfo(self):
        active_map = get_active_map_or_none()
        group_long_names = list_group_long_names(active_map)

        parcel_layer = arcpy.Parameter(
            displayName="Parcel Layer (with selection)",
            name="parcel_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        height_group = arcpy.Parameter(
            displayName="Height Group Layer",
            name="height_group",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        height_group.filter.type = "ValueList"
        height_group.filter.list = group_long_names

        velocity_group = arcpy.Parameter(
            displayName="Velocity Group Layer",
            name="velocity_group",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        velocity_group.filter.type = "ValueList"
        velocity_group.filter.list = group_long_names

        depth_group = arcpy.Parameter(
            displayName="Depth Group Layer",
            name="depth_group",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        depth_group.filter.type = "ValueList"
        depth_group.filter.list = group_long_names

        return [parcel_layer, height_group, velocity_group, depth_group]

    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        active_map = get_active_map_or_none()
        if active_map is None:
            return
        group_long_names = list_group_long_names(active_map)
        parameters_by_name = {parameter.name: parameter for parameter in parameters}
        for group_parameter_name in ("height_group", "velocity_group", "depth_group"):
            parameters_by_name[group_parameter_name].filter.list = group_long_names
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        try:
            run_extraction(parameters)
        except arcpy.ExecuteError:
            raise
        except Exception as unexpected_error:
            arcpy.AddError(f"[EPS] Unexpected error: {unexpected_error}")
            arcpy.AddError(traceback.format_exc())
            raise

    def postExecute(self, parameters):
        return


def run_extraction(parameters):
    parameters_by_name = {parameter.name: parameter for parameter in parameters}
    parcel_layer_parameter = parameters_by_name["parcel_layer"]
    height_group_long_name = parameters_by_name["height_group"].valueAsText
    velocity_group_long_name = parameters_by_name["velocity_group"].valueAsText
    depth_group_long_name = parameters_by_name["depth_group"].valueAsText

    overall_start = time.perf_counter()
    log("=" * 70)
    log("Extract Parcel Stats — starting")
    log(f"Parcel layer:   {parcel_layer_parameter.valueAsText}")
    log(f"Height group:   {height_group_long_name}")
    log(f"Velocity group: {velocity_group_long_name}")
    log(f"Depth group:    {depth_group_long_name}")
    log("=" * 70)

    require_spatial_analyst_or_fail()
    arcpy.CheckOutExtension("Spatial")
    try:
        arcpy.env.overwriteOutput = True

        active_map = get_active_map_or_none()
        if active_map is None:
            fail("No active map. Open a map and try again.")

        parcel_layer = resolve_layer_in_map(parcel_layer_parameter, active_map)
        log(f"Resolved parcel layer to live TOC layer: {parcel_layer.longName}")

        require_parcel_selection_or_fail(parcel_layer, active_map)

        parcel_id_field = detect_parcel_id_field_or_fail(parcel_layer)
        parcel_spi_field = detect_parcel_spi_field(parcel_layer)
        log(f"Detected ID field: {parcel_id_field}; SPI field: {parcel_spi_field or '(none)'}")

        zone_layer_name = prepare_selected_zone_layer(parcel_layer)

        selected_parcels = list_selected_parcels(zone_layer_name, parcel_id_field, parcel_spi_field)
        log(f"Loaded {len(selected_parcels)} parcel row(s) from the zone layer.")

        log("")
        log("Collecting visible rasters per group (respecting ancestor visibility):")
        rasters_by_group_type = {
            "Height":   collect_visible_rasters(active_map, height_group_long_name,   "Height"),
            "Velocity": collect_visible_rasters(active_map, velocity_group_long_name, "Velocity"),
            "Depth":    collect_visible_rasters(active_map, depth_group_long_name,    "Depth"),
        }

        per_parcel_summary = seed_per_parcel_summary(selected_parcels)

        for group_type_label in GROUP_TYPES:
            log("")
            log(f"--- Processing {group_type_label} group ---")
            aggregated_for_group = compute_group_stats(
                zone_layer_name,
                rasters_by_group_type[group_type_label],
                group_type_label,
                parcel_id_field,
            )
            merge_group_into_summary(per_parcel_summary, aggregated_for_group, group_type_label)
            log(f"{group_type_label}: {len(aggregated_for_group)} parcel(s) had data.")

        log("")
        log_per_parcel_summary(per_parcel_summary)

        log("")
        log(f"Done. Parcels reported: {len(per_parcel_summary)}. Elapsed: {time.perf_counter() - overall_start:.2f}s.")
    finally:
        cleanup_zone_layer()
        try:
            arcpy.CheckInExtension("Spatial")
        except Exception:
            pass


def log(message_text):
    arcpy.AddMessage(f"[EPS] {message_text}")


def warn(message_text):
    arcpy.AddWarning(f"[EPS] {message_text}")


def fail(message_text):
    arcpy.AddError(f"[EPS] {message_text}")
    raise arcpy.ExecuteError


def get_active_map_or_none():
    try:
        return arcpy.mp.ArcGISProject("CURRENT").activeMap
    except Exception:
        return None


def list_group_long_names(active_map):
    if active_map is None:
        return []
    group_long_names = []
    for layer in active_map.listLayers():
        if layer.isGroupLayer:
            group_long_names.append(layer.longName)
    return group_long_names


def require_spatial_analyst_or_fail():
    status = arcpy.CheckExtension("Spatial")
    if status != "Available":
        fail(f"Spatial Analyst extension is not available (status: {status}).")


def resolve_layer_in_map(layer_parameter, active_map):
    candidate_names = []
    layer_value = layer_parameter.value
    if hasattr(layer_value, "longName"):
        candidate_names.append(layer_value.longName)
    if hasattr(layer_value, "name"):
        candidate_names.append(layer_value.name)
    text_value = layer_parameter.valueAsText
    if text_value:
        candidate_names.append(text_value)
        candidate_names.append(text_value.split("\\")[-1])

    for layer in active_map.listLayers():
        if layer.longName in candidate_names or layer.name in candidate_names:
            return layer

    fail(
        f"Could not find layer '{text_value}' in the active map. "
        "Pick the layer from the map's table of contents (not a path on disk)."
    )


def count_selected_features(parcel_layer):
    selection_set = None
    selection_api_error = None
    try:
        selection_set = parcel_layer.getSelectionSet()
    except Exception as selection_exception:
        selection_api_error = f"{type(selection_exception).__name__}: {selection_exception}"

    if selection_set is not None:
        return len(selection_set), "Layer.getSelectionSet()"

    if selection_api_error is not None:
        log(f"  Layer.getSelectionSet() raised: {selection_api_error}")

    try:
        fid_set = arcpy.Describe(parcel_layer).FIDSet
        fallback_count = 0 if not fid_set else len(fid_set.split(";"))
        return fallback_count, "Describe.FIDSet (fallback)"
    except Exception as fid_exception:
        log(f"  Describe.FIDSet raised: {type(fid_exception).__name__}: {fid_exception}")
        return 0, "no API responded"


def require_parcel_selection_or_fail(parcel_layer, active_map):
    selected_count, source_api = count_selected_features(parcel_layer)
    log(f"Selection check via {source_api}: {selected_count} selected feature(s) on '{parcel_layer.longName}'.")
    if selected_count > 0:
        return

    other_layers_with_selection = find_other_layers_with_selection(active_map, parcel_layer.longName)
    if other_layers_with_selection:
        log("")
        log("FYI — selections DO exist on these OTHER layers in the active map:")
        for other_layer_long_name, other_selected_count in other_layers_with_selection:
            log(f"  - '{other_layer_long_name}': {other_selected_count} feature(s) selected")
        fail(
            f"No selection on the chosen layer '{parcel_layer.longName}'. "
            "Selection exists on a different layer (see list above). "
            "Re-open the tool and pick the layer that actually has the selection."
        )

    fail(
        "No selection found on ANY layer in the active map. "
        "Select one or more parcels first (Map ribbon → Select), then re-run."
    )


def find_other_layers_with_selection(active_map, chosen_layer_long_name):
    other_layers_with_selection = []
    for layer in active_map.listLayers():
        if layer.longName == chosen_layer_long_name:
            continue
        try:
            selection_set = layer.getSelectionSet()
        except Exception:
            continue
        if selection_set is None:
            continue
        if len(selection_set) > 0:
            other_layers_with_selection.append((layer.longName, len(selection_set)))
    return other_layers_with_selection


def detect_parcel_id_field_or_fail(parcel_layer):
    available_field_names = [field.name for field in arcpy.ListFields(parcel_layer)]
    matched_field = match_candidate_field(available_field_names, PARCEL_ID_FIELD_CANDIDATES)
    if matched_field is not None:
        if matched_field.upper().endswith("OBJECTID"):
            warn(
                "Falling back to OBJECTID as the parcel ID field — no PARCEL_PFI / PROPERTY_PFI / "
                "PROP_PFI / PFI field was found."
            )
            warn(f"  Available fields on this layer: {', '.join(available_field_names)}")
        return matched_field
    fail(
        "Could not find a parcel ID field on the layer. "
        f"Looked for: {', '.join(PARCEL_ID_FIELD_CANDIDATES)}. "
        f"Available fields: {', '.join(available_field_names)}"
    )


def detect_parcel_spi_field(parcel_layer):
    available_field_names = [field.name for field in arcpy.ListFields(parcel_layer)]
    return match_candidate_field(available_field_names, PARCEL_SPI_FIELD_CANDIDATES)


def match_candidate_field(available_field_names, candidate_names):
    upper_available_by_upper = {available_name.upper(): available_name for available_name in available_field_names}
    for candidate in candidate_names:
        if candidate in upper_available_by_upper:
            return upper_available_by_upper[candidate]
        for upper_available_name, original_available_name in upper_available_by_upper.items():
            if upper_available_name.endswith("." + candidate) or upper_available_name.endswith("_" + candidate):
                return original_available_name
    return None


def prepare_selected_zone_layer(parcel_layer):
    selected_oids = get_selected_oids(parcel_layer)
    if not selected_oids:
        fail("Internal: selection vanished between selection check and zone-layer build.")

    if len(selected_oids) > 999:
        warn(
            f"Large selection ({len(selected_oids)} features). Using a long IN clause; "
            "may hit SQL limits on some data sources."
        )

    oid_field_name = arcpy.Describe(parcel_layer).OIDFieldName
    oid_list_text = ", ".join(str(int(oid)) for oid in selected_oids)
    where_clause = f"{oid_field_name} IN ({oid_list_text})"

    cleanup_zone_layer()
    arcpy.management.MakeFeatureLayer(parcel_layer, ZONE_LAYER_NAME, where_clause)

    materialised_count = int(arcpy.management.GetCount(ZONE_LAYER_NAME).getOutput(0))
    log(f"Built zone layer '{ZONE_LAYER_NAME}' with {materialised_count} feature(s).")
    if materialised_count == 0:
        fail("Could not materialise selection on the zone layer (count = 0 after MakeFeatureLayer).")
    if materialised_count != len(selected_oids):
        warn(
            f"Zone layer count ({materialised_count}) differs from selected OID count "
            f"({len(selected_oids)}). Proceeding with the zone layer's count."
        )
    return ZONE_LAYER_NAME


def get_selected_oids(parcel_layer):
    try:
        selection_set = parcel_layer.getSelectionSet()
        if selection_set is not None and len(selection_set) > 0:
            return sorted(selection_set)
    except Exception:
        pass
    try:
        fid_set = arcpy.Describe(parcel_layer).FIDSet
    except Exception:
        fid_set = ""
    if fid_set:
        return [int(oid) for oid in fid_set.split(";")]
    return []


def cleanup_zone_layer():
    try:
        if arcpy.Exists(ZONE_LAYER_NAME):
            arcpy.management.Delete(ZONE_LAYER_NAME)
    except Exception:
        pass


def list_selected_parcels(parcel_layer, parcel_id_field, parcel_spi_field):
    cursor_fields = [parcel_id_field]
    if parcel_spi_field is not None:
        cursor_fields.append(parcel_spi_field)

    selected_parcels = []
    with arcpy.da.SearchCursor(parcel_layer, cursor_fields) as cursor:
        for row in cursor:
            parcel_id = row[0]
            parcel_spi = row[1] if parcel_spi_field is not None else ""
            selected_parcels.append({"id": parcel_id, "spi": parcel_spi})
    return selected_parcels


def seed_per_parcel_summary(selected_parcels):
    per_parcel_summary = {}
    for parcel in selected_parcels:
        per_parcel_summary[parcel["id"]] = {
            "spi":      parcel["spi"],
            "Height":   None,
            "Velocity": None,
            "Depth":    None,
        }
    return per_parcel_summary


def collect_visible_rasters(active_map, group_long_name, group_type_label):
    if not group_long_name:
        log(f"  {group_type_label}: no group provided; skipping.")
        return []

    visible_rasters = list_visible_rasters_under(active_map, group_long_name)
    if not visible_rasters:
        log(f"  {group_type_label}: no visible rasters under '{group_long_name}'; skipping.")
        return []

    log(f"  {group_type_label}: {len(visible_rasters)} visible raster(s) under '{group_long_name}':")
    for raster_layer in visible_rasters:
        log(f"    - {raster_layer.longName}")
    return visible_rasters


def list_visible_rasters_under(active_map, group_long_name):
    all_layers = active_map.listLayers()
    visibility_by_long_name = {layer.longName: layer.visible for layer in all_layers}
    group_prefix = group_long_name + "\\"

    visible_rasters = []
    for layer in all_layers:
        if not layer.isRasterLayer:
            continue
        if not layer.longName.startswith(group_prefix):
            continue
        if not is_ancestor_chain_visible(layer.longName, visibility_by_long_name):
            continue
        visible_rasters.append(layer)
    return visible_rasters


def is_ancestor_chain_visible(long_name, visibility_by_long_name):
    parts = long_name.split("\\")
    for end_index in range(1, len(parts) + 1):
        ancestor_long_name = "\\".join(parts[:end_index])
        if not visibility_by_long_name.get(ancestor_long_name, True):
            return False
    return True


def compute_group_stats(parcel_layer, raster_layers, group_type_label, parcel_id_field):
    total_rasters = len(raster_layers)
    arcpy.SetProgressor("step", f"Extracting {group_type_label} stats", 0, total_rasters, 1)
    aggregated_per_parcel = {}
    for raster_index, raster_layer in enumerate(raster_layers, start=1):
        arcpy.SetProgressorLabel(f"{group_type_label}: {raster_layer.name} ({raster_index}/{total_rasters})")
        run_zonal_stats_into(
            aggregated_per_parcel,
            parcel_layer,
            parcel_id_field,
            raster_layer,
            group_type_label,
            raster_index,
        )
        arcpy.SetProgressorPosition()
    arcpy.ResetProgressor()
    return aggregated_per_parcel


def run_zonal_stats_into(aggregated_per_parcel, parcel_layer, parcel_id_field, raster_layer, group_type_label, raster_index):
    start_time = time.perf_counter()
    output_table_in_memory = f"memory\\eps_zs_{group_type_label.lower()}_{raster_index}"
    if arcpy.Exists(output_table_in_memory):
        arcpy.management.Delete(output_table_in_memory)

    log(f"  {group_type_label} [{raster_index}]: ZonalStatisticsAsTable on '{raster_layer.longName}'")
    try:
        arcpy.sa.ZonalStatisticsAsTable(
            parcel_layer,
            parcel_id_field,
            raster_layer,
            output_table_in_memory,
            "DATA",
            "MIN_MAX",
        )
    except arcpy.ExecuteError:
        warn(f"    Skipped (no overlap or tool error): {arcpy.GetMessages(2)}")
        return

    updated_parcel_count = merge_zonal_table_into(
        aggregated_per_parcel,
        output_table_in_memory,
        parcel_id_field,
        raster_layer.longName,
    )
    try:
        arcpy.management.Delete(output_table_in_memory)
    except Exception:
        pass
    log(f"    -> {updated_parcel_count} parcel(s) updated in {time.perf_counter() - start_time:.2f}s")


def merge_zonal_table_into(aggregated_per_parcel, zonal_table, parcel_id_field, raster_long_name):
    updated_count = 0
    with arcpy.da.SearchCursor(zonal_table, [parcel_id_field, "MIN", "MAX"]) as cursor:
        for parcel_id, min_value, max_value in cursor:
            existing = aggregated_per_parcel.get(parcel_id)
            if existing is None:
                aggregated_per_parcel[parcel_id] = {
                    "min":     min_value,
                    "max":     max_value,
                    "sources": [raster_long_name],
                }
            else:
                if min_value is not None and (existing["min"] is None or min_value < existing["min"]):
                    existing["min"] = min_value
                if max_value is not None and (existing["max"] is None or max_value > existing["max"]):
                    existing["max"] = max_value
                existing["sources"].append(raster_long_name)
            updated_count += 1
    return updated_count


def merge_group_into_summary(per_parcel_summary, aggregated_for_group, group_type_label):
    for parcel_id, aggregate in aggregated_for_group.items():
        existing = per_parcel_summary.get(parcel_id)
        if existing is None:
            existing = {"spi": "", "Height": None, "Velocity": None, "Depth": None}
            per_parcel_summary[parcel_id] = existing
        existing[group_type_label] = aggregate


def log_per_parcel_summary(per_parcel_summary):
    if not per_parcel_summary:
        warn("No parcels to summarise.")
        return

    log("=" * 70)
    log("PER-PARCEL RESULTS")
    log("=" * 70)
    for parcel_id in sorted(per_parcel_summary):
        summary = per_parcel_summary[parcel_id]
        spi_text = summary["spi"] if summary["spi"] else "-"
        log("")
        log(f"Parcel {parcel_id}   (SPI: {spi_text})")
        header_line = f"  {'Group':<10}{'Min':<14}{'Max':<14}{'Sources'}"
        log(header_line)
        log("  " + "-" * 68)
        for group_type_label in GROUP_TYPES:
            log("  " + format_group_row(group_type_label, summary[group_type_label]))


def format_group_row(group_type_label, aggregate):
    if aggregate is None:
        return f"{group_type_label:<10}{'None':<14}{'None':<14}-"
    min_text = "None" if aggregate["min"] is None else f"{aggregate['min']:.4f}"
    max_text = "None" if aggregate["max"] is None else f"{aggregate['max']:.4f}"
    sources_text = "; ".join(aggregate["sources"])
    return f"{group_type_label:<10}{min_text:<14}{max_text:<14}{sources_text}"
