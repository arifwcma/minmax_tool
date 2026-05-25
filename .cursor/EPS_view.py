# -*- coding: utf-8 -*-
import arcpy

class Toolbox:
    def __init__(self):
        self.label = "Toolbox"
        self.alias = "toolbox"
        self.tools = [Tool]

class Tool:
    def __init__(self):
        self.label = "Tool"
        self.description = "Extracts min/max values from height and velocity raster groups for selected parcels."

    def getParameterInfo(self):
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        map_obj = aprx.activeMap
        group_names = [lyr.name for lyr in map_obj.listLayers() if lyr.isGroupLayer]

        p0 = arcpy.Parameter(
            displayName="Parcel Layer",
            name="parcel_layer",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input"
        )
        p0.value = "Property\Vicmap_Parcel\Parcel Map Polygons - Vicmap Property (PARCEL_MP)"

        p1 = arcpy.Parameter(
            displayName="Height Group Layer",
            name="height_group",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        p1.filter.type = "ValueList"
        p1.filter.list = group_names
        p1.value = "Mount William - Heights"

        p2 = arcpy.Parameter(
            displayName="Velocity Group Layer",
            name="velocity_group",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        p2.filter.type = "ValueList"
        p2.filter.list = group_names
        p2.value = "Mount William - Velocity"

        p3 = arcpy.Parameter(
            displayName="Depth Group Layer",
            name="depth_group",
            datatype="GPString",
            parameterType="Required",
            direction="Input"
        )
        p3.filter.type = "ValueList"
        p3.filter.list = group_names
        p3.value = "Mount William - Depths"

        return [p0, p1, p2, p3]



    def isLicensed(self):
        return True

    def updateParameters(self, parameters):
        return

    def updateMessages(self, parameters):
        return

    def execute(self, parameters, messages):
        import arcpy

        parcel_layer = parameters[0].value
        height_group_name = parameters[1].valueAsText
        velocity_group_name = parameters[2].valueAsText
        depth_group_name = parameters[3].valueAsText

        aprx = arcpy.mp.ArcGISProject("CURRENT")
        map_obj = aprx.activeMap
        arcpy.env.overwriteOutput = True

        arcpy.management.MakeFeatureLayer(parcel_layer, "selected_parcels")
        arcpy.management.SelectLayerByAttribute("selected_parcels", "SUBSET_SELECTION")

        height_group = next((lyr for lyr in map_obj.listLayers() if lyr.name == height_group_name and lyr.isGroupLayer), None)
        if height_group is None:
            raise Exception(f"Height group layer '{height_group_name}' not found.")

        velocity_group = next((lyr for lyr in map_obj.listLayers() if lyr.name == velocity_group_name and lyr.isGroupLayer), None)
        if velocity_group is None:
            raise Exception(f"Velocity group layer '{velocity_group_name}' not found.")

        depth_group = next((lyr for lyr in map_obj.listLayers() if lyr.name == depth_group_name and lyr.isGroupLayer), None)
        if depth_group is None:
            raise Exception(f"Depth group layer '{depth_group_name}' not found.")

        height_layers = self.get_raster_layers(height_group)
        velocity_layers = self.get_raster_layers(velocity_group)
        depth_layers = self.get_raster_layers(depth_group)



        if not height_layers:
            raise Exception("No visible raster layers found in the selected Height group.")
        if not velocity_layers:
            raise Exception("No visible raster layers found in the selected Velocity group.")
        if not depth_layers:
            raise Exception("No visible raster layers found in the selected Depth group.")

        fields = ["PARCEL_PFI", "PARCEL_SPI"]

        with arcpy.da.SearchCursor("selected_parcels", fields, spatial_reference=map_obj.spatialReference) as cursor:
            for row in cursor:
                parcel_id = row[0]
                parcel_spi = row[1]
                sql = f"PARCEL_PFI = '{parcel_id}'"
                arcpy.management.MakeFeatureLayer("selected_parcels", "temp_lyr", sql)

                min_h, max_h, h_layer_name = None, None, None
                for r in height_layers:
                    try:
                        clipped = arcpy.management.Clip(r, "#", "in_memory/clipped_h", "temp_lyr", "#", "ClippingGeometry")
                        min_h = float(arcpy.management.GetRasterProperties(clipped, "MINIMUM").getOutput(0))
                        max_h = float(arcpy.management.GetRasterProperties(clipped, "MAXIMUM").getOutput(0))
                        h_layer_name = r.name
                        arcpy.management.Delete("in_memory/clipped_h")
                        break
                    except arcpy.ExecuteError:
                        continue

                min_v, max_v, v_layer_name = None, None, None
                for r in velocity_layers:
                    try:
                        clipped = arcpy.management.Clip(r, "#", "in_memory/clipped_v", "temp_lyr", "#", "ClippingGeometry")
                        min_v = float(arcpy.management.GetRasterProperties(clipped, "MINIMUM").getOutput(0))
                        max_v = float(arcpy.management.GetRasterProperties(clipped, "MAXIMUM").getOutput(0))
                        v_layer_name = r.name
                        arcpy.management.Delete("in_memory/clipped_v")
                        break
                    except arcpy.ExecuteError:
                        continue

                min_d, max_d, d_layer_name = None, None, None
                for r in depth_layers:
                    try:
                        clipped = arcpy.management.Clip(r, "#", "in_memory/clipped_d", "temp_lyr", "#", "ClippingGeometry")
                        min_d = float(arcpy.management.GetRasterProperties(clipped, "MINIMUM").getOutput(0))
                        max_d = float(arcpy.management.GetRasterProperties(clipped, "MAXIMUM").getOutput(0))
                        d_layer_name = r.name
                        arcpy.management.Delete("in_memory/clipped_d")
                        break
                    except arcpy.ExecuteError:
                        continue

                if any([min_h is not None, min_v is not None, min_d is not None]):
                    output_lines = []
                    output_lines.append(f"\nParcel-{parcel_id}\n")
                    output_lines.append(f"{'Layer':<30}{'Type':<12}{'Min':<30}{'Max':<30}")
                    output_lines.append("-" * 82)
                    output_lines.append(f"{h_layer_name or 'None':<30}{'Height':<12}{str(min_h) if min_h is not None else 'None':<30}{str(max_h) if max_h is not None else 'None':<30}")
                    output_lines.append(f"{v_layer_name or 'None':<30}{'Velocity':<12}{str(min_v) if min_v is not None else 'None':<30}{str(max_v) if max_v is not None else 'None':<30}")
                    output_lines.append(f"{d_layer_name or 'None':<30}{'Depth':<12}{str(min_d) if min_d is not None else 'None':<30}{str(max_d) if max_d is not None else 'None':<30}")
                    output_lines.append("\n")
                    arcpy.AddMessage("\n".join(output_lines))

                arcpy.management.Delete("temp_lyr")



    class LayerNode:
        def __init__(self, name, layer=None):
            self.name = name
            self.layer = layer
            self.children = {}

    def build_layer_tree(self, all_layers):
        root = self.LayerNode("root")
        layer_map = {l.longName: l for l in all_layers}
        for long_name in sorted(layer_map):
            parts = long_name.split("\\")
            current = root
            for i, part in enumerate(parts):
                if part not in current.children:
                    name_path = "\\".join(parts[:i+1])
                    lyr = layer_map.get(name_path)
                    current.children[part] = self.LayerNode(part, lyr)
                current = current.children[part]
        return root

    def collect_visible_rasters(self, node, ancestors_visible=True):
        visible_rasters = []
        current_visible = node.layer.visible if node.layer else True
        if not ancestors_visible or not current_visible:
            return []
        for child in node.children.values():
            if child.layer and child.layer.isRasterLayer:
                if child.layer.visible and current_visible and ancestors_visible:
                    visible_rasters.append(child.layer)
            visible_rasters.extend(self.collect_visible_rasters(child, ancestors_visible and current_visible))
        return visible_rasters

    def get_raster_layers(self, group_layer):
        all_layers = group_layer.listLayers()
        tree = self.build_layer_tree(all_layers)
        return self.collect_visible_rasters(tree)

    def postExecute(self, parameters):
        return
