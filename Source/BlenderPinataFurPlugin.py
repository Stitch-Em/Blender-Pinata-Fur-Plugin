# -----------------------------------------------------------------------------------------------------------
# Author: @SolarCookies - Sebastian Robinson
# Palette Creator integration by SolarCookies
# Copyright: MIT License
# Blender Version: 5.1.0
# Info: Shell Fur generator for Pinatas with integrated palette color painter.
#       Fur color is driven by a grayscale painted texture looked up through a palette LUT.
# -----------------------------------------------------------------------------------------------------------

bl_info = {
    "name": "Shell Fur Tool",
    "author": "SolarCookies",
    "version": (0, 2, 0),
    "blender": (5, 1, 0),
    "location": "3D Viewport > Sidebar > Shell Fur Tool",
    "description": "Shell fur generator with integrated palette painter for pinatas",
    "category": "Graphics",
}

import bpy
import json
import numpy as np
from bpy.props import (
    FloatVectorProperty,
    FloatProperty,
    IntProperty,
    CollectionProperty,
    StringProperty,
    BoolProperty,
    PointerProperty,
)
from bpy.types import PropertyGroup, Panel, Operator, UIList


# ============================================================================
# PALETTE CREATOR — color space helper
# ============================================================================

def _linear_to_srgb(c):
    """Convert a numpy array of linear RGB values to sRGB (IEC 61966-2-1)."""
    c = np.clip(c, 0.0, 1.0)
    return np.where(
        c <= 0.0031308,
        12.92 * c,
        1.055 * np.power(c, 1.0 / 2.4) - 0.055,
    )


# ---------------------------------------------------------------------------
# Default palette entries
# ---------------------------------------------------------------------------
DEFAULT_PALETTE = [
    ((0.0,  0.0,  1.0), 0.000, "1"),
    ((0.5,  0.0,  1.0), 0.050, "2"),
    ((1.0,  0.0,  0.0), 0.100, "3"),
    ((1.0,  0.3,  0.0), 0.150, "4"),
    ((0.0,  0.8,  0.0), 0.200, "5"),
    ((0.0,  0.5,  0.0), 0.250, "6"),
    ((1.0,  0.5,  0.0), 0.300, "7"),
    ((1.0,  0.8,  0.0), 0.350, "8"),
    ((0.6,  0.0,  0.8), 0.400, "9"),
    ((0.8,  0.0,  0.5), 0.450, "10"),
    ((0.0,  0.8,  0.8), 0.500, "11"),
    ((0.0,  0.5,  0.8), 0.550, "12"),
    ((1.0,  1.0,  0.0), 0.600, "13"),
    ((0.6,  1.0,  0.0), 0.650, "14"),
    ((1.0,  0.4,  0.7), 0.700, "15"),
    ((0.3,  0.6,  1.0), 0.750, "16"),
    ((0.8,  0.5,  0.2), 0.800, "17"),
    ((0.5,  1.0,  0.5), 0.850, "18"),
    ((1.0,  0.7,  0.4), 0.900, "19"),
    ((0.9,  0.9,  0.9), 0.950, "20"),
    ((1.0,  1.0,  1.0), 1.000, "21"),
]


# ============================================================================
# PALETTE CREATOR — Property Groups
# ============================================================================

def _on_entry_changed(self, context):
    """Auto-bake the LUT whenever a palette entry colour or grayscale value changes."""
    if context.scene:
        _bake_lut_now(context.scene.gpp_props)


class GPP_PaletteEntry(PropertyGroup):
    display_color: FloatVectorProperty(
        name="Display Color",
        subtype="COLOR",
        size=3, min=0.0, max=1.0,
        default=(1.0, 1.0, 1.0),
        update=_on_entry_changed,
    )
    grayscale_value: FloatProperty(
        name="Grayscale Value",
        description="Value written to the texture (0=black, 1=white)",
        min=0.0, max=1.0, default=0.0,
        update=_on_entry_changed,
    )
    label: StringProperty(name="Label", default="Swatch")


class GPP_Palette(PropertyGroup):
    name: StringProperty(name="Palette Name", default="Palette")
    entries: CollectionProperty(type=GPP_PaletteEntry)
    active_index: IntProperty(name="Active Entry", default=0)


# ============================================================================
# PALETTE CREATOR — LUT bake helper
# ============================================================================

def _bake_lut_now(props):
    """Bake the active palette into the LUT image. Safe to call from an update callback."""
    if len(props.palettes) == 0 or props.active_palette_index >= len(props.palettes):
        return
    pal = props.palettes[props.active_palette_index]
    if len(pal.entries) == 0:
        return

    lut_name = props.lut_image_name
    width = 256

    lut_img = bpy.data.images.get(lut_name)
    if lut_img is None:
        lut_img = bpy.data.images.new(lut_name, width=width, height=1, alpha=True)
    elif lut_img.size[0] != width or lut_img.size[1] != 1:
        bpy.data.images.remove(lut_img)
        lut_img = bpy.data.images.new(lut_name, width=width, height=1, alpha=True)

    lut_img.colorspace_settings.name = "Non-Color"

    entries = sorted(
        [(e.grayscale_value, tuple(e.display_color)) for e in pal.entries],
        key=lambda x: x[0],
    )
    gray_vals = np.array([e[0] for e in entries], dtype=np.float32)
    colors    = np.array([e[1] for e in entries], dtype=np.float32)
    pixel_uv  = (np.arange(width, dtype=np.float32) + 0.5) / width
    nearest   = np.argmin(np.abs(pixel_uv[:, None] - gray_vals[None, :]), axis=1)
    rgba      = np.ones((width, 4), dtype=np.float32)
    rgba[:, :3] = colors[nearest]
    lut_img.pixels[:] = rgba.ravel().tolist()
    lut_img.update()


def _on_palette_switch(self, context):
    """Auto-bakes LUT when the active palette changes."""
    _bake_lut_now(self)


class GPP_SceneProps(PropertyGroup):
    palettes: CollectionProperty(type=GPP_Palette)
    active_palette_index: IntProperty(
        name="Active Palette", default=0, update=_on_palette_switch
    )
    brush_size: IntProperty(
        name="Brush Size", description="Hard brush radius in pixels",
        min=1, max=256, default=10,
    )
    columns: IntProperty(
        name="Columns", description="Number of columns in the palette grid",
        min=1, max=16, default=4,
    )
    show_grayscale_value: BoolProperty(
        name="Show Grayscale Values", default=True,
    )
    painted_image: PointerProperty(
        type=bpy.types.Image,
        name="Painted Texture",
        description="Grayscale image painted with palette values; used as the fur colour source",
    )
    lut_image_name: StringProperty(
        name="LUT Image Name", default="GPP_LUT",
    )
    material_name: StringProperty(
        name="Material Name", default="GPP_Material",
    )
    baked_color_image_name: StringProperty(
        name="Baked Color Image", default="GPP_Color_Baked",
    )


# ============================================================================
# PALETTE CREATOR — Helpers
# ============================================================================

def _current_palette(props):
    """Return the active GPP_Palette, or None if the list is empty."""
    if len(props.palettes) == 0 or props.active_palette_index >= len(props.palettes):
        return None
    return props.palettes[props.active_palette_index]


def _populate_palette(pal):
    """Fill a GPP_Palette with the default entries."""
    pal.entries.clear()
    for color, gray, lbl in DEFAULT_PALETTE:
        e = pal.entries.add()
        e.display_color = color
        e.grayscale_value = gray
        e.label = lbl
    pal.active_index = 0


def _ensure_palettes(props):
    """Create the Default palette if no palettes exist yet."""
    if len(props.palettes) == 0:
        pal = props.palettes.add()
        pal.name = "Default"
        _populate_palette(pal)
        props.active_palette_index = 0


# ============================================================================
# PALETTE CREATOR — Operators
# ============================================================================

class GPP_OT_InitPalette(Operator):
    bl_idname = "gpp.init_palette"
    bl_label = "Reset to Default Palette"
    bl_description = "Reset the active palette to the default entries"

    def execute(self, context):
        props = context.scene.gpp_props
        pal = _current_palette(props)
        if pal is None:
            _ensure_palettes(props)
        else:
            _populate_palette(pal)
        return {"FINISHED"}


class GPP_OT_AddEntry(Operator):
    bl_idname = "gpp.add_entry"
    bl_label = "Add Palette Entry"

    def execute(self, context):
        pal = _current_palette(context.scene.gpp_props)
        if pal is None:
            return {"CANCELLED"}
        if len(pal.entries) > 0:
            max_val = max(entry.grayscale_value for entry in pal.entries)
            next_val = min(1.0, round(max_val + 0.05, 3))
        else:
            next_val = 0.0
        e = pal.entries.add()
        e.display_color = (1.0, 1.0, 1.0)
        e.grayscale_value = next_val
        e.label = str(len(pal.entries))
        pal.active_index = len(pal.entries) - 1
        return {"FINISHED"}


class GPP_OT_RemoveEntry(Operator):
    bl_idname = "gpp.remove_entry"
    bl_label = "Remove Palette Entry"

    def execute(self, context):
        pal = _current_palette(context.scene.gpp_props)
        if pal is None or len(pal.entries) == 0:
            return {"CANCELLED"}
        pal.entries.remove(pal.active_index)
        pal.active_index = max(0, pal.active_index - 1)
        return {"FINISHED"}


class GPP_OT_SelectEntry(Operator):
    bl_idname = "gpp.select_entry"
    bl_label = "Select Palette Entry"
    bl_description = "Select this colour and configure the paint brush"

    index: IntProperty()

    def execute(self, context):
        pal = _current_palette(context.scene.gpp_props)
        if pal is None or self.index >= len(pal.entries):
            return {"CANCELLED"}
        pal.active_index = self.index
        entry = pal.entries[self.index]
        gray = entry.grayscale_value

        # Configure the image paint brush
        paint = context.tool_settings.image_paint
        if paint:
            # Use unified paint settings (Paint.unified_paint_settings in Blender 5.x)
            ups = paint.unified_paint_settings
            ups.use_unified_color = True
            ups.color = (gray, gray, gray)
            ups.secondary_color = (gray, gray, gray)

            # Activate "Paint Pixel Art" whenever it isn't already the active brush.
            if paint.brush is None or paint.brush.name != "Paint Pixel Art":
                override_area = None
                override_window = None
                for win in context.window_manager.windows:
                    for area in win.screen.areas:
                        if area.type == 'IMAGE_EDITOR':
                            override_area = area
                            override_window = win
                            break
                    if override_area:
                        break
                if override_area is None:
                    for win in context.window_manager.windows:
                        for area in win.screen.areas:
                            if area.type == 'VIEW_3D':
                                override_area = area
                                override_window = win
                                break
                        if override_area:
                            break
                try:
                    kw = dict(
                        asset_library_type='ESSENTIALS',
                        relative_asset_identifier=(
                            'brushes/essentials_brushes-mesh_texture.blend'
                            '/Brush/Paint Pixel Art'
                        ),
                    )
                    if override_area:
                        with context.temp_override(window=override_window, area=override_area):
                            bpy.ops.brush.asset_activate(**kw)
                    else:
                        bpy.ops.brush.asset_activate(**kw)
                except Exception:
                    pass

            # Set colour and pixel-art settings on the active brush.
            brush = paint.brush
            if brush:
                brush.color = (gray, gray, gray)
                brush.secondary_color = (gray, gray, gray)
                brush.blend = 'MIX'
                brush.strength = 1.0
                brush.hardness = 1.0
                brush.use_paint_antialiasing = False
                brush.stroke_method = 'DOTS'
                if hasattr(brush, 'use_pressure_strength'):
                    brush.use_pressure_strength = False
                if hasattr(brush, 'use_pressure_size'):
                    brush.use_pressure_size = False

        self.report({"INFO"}, f"'{entry.label}' -> grayscale {gray:.3f}")
        return {"FINISHED"}


class GPP_OT_PaintStamp(Operator):
    bl_idname = "gpp.paint_stamp"
    bl_label = "Paint Stamp"
    bl_options = {"INTERNAL"}

    uv_x: FloatProperty()
    uv_y: FloatProperty()
    image_name: StringProperty()

    def execute(self, context):
        props = context.scene.gpp_props
        pal = _current_palette(props)
        if pal is None or pal.active_index >= len(pal.entries):
            return {"CANCELLED"}

        image = bpy.data.images.get(self.image_name)
        if image is None:
            self.report({"WARNING"}, f"Image '{self.image_name}' not found")
            return {"CANCELLED"}

        gray = pal.entries[pal.active_index].grayscale_value
        radius = props.brush_size
        width, height = image.size
        pixels = np.array(image.pixels[:], dtype=np.float32).reshape(height, width, 4)
        cx = int(self.uv_x * width)
        cy = int(self.uv_y * height)
        x0, x1 = max(0, cx - radius), min(width,  cx + radius + 1)
        y0, y1 = max(0, cy - radius), min(height, cy + radius + 1)
        xx, yy = np.meshgrid(np.arange(x0, x1), np.arange(y0, y1))
        mask = ((xx - cx) ** 2 + (yy - cy) ** 2) <= radius ** 2
        pixels[y0:y1, x0:x1, 0][mask] = gray
        pixels[y0:y1, x0:x1, 1][mask] = gray
        pixels[y0:y1, x0:x1, 2][mask] = gray
        image.pixels[:] = pixels.ravel().tolist()
        image.update()
        return {"FINISHED"}


class GPP_OT_AddPalette(Operator):
    bl_idname = "gpp.add_palette"
    bl_label = "Add Palette"
    bl_description = "Add a new named palette populated with the default entries"

    def execute(self, context):
        props = context.scene.gpp_props
        pal = props.palettes.add()
        pal.name = f"Palette {len(props.palettes)}"
        _populate_palette(pal)
        props.active_palette_index = len(props.palettes) - 1
        return {"FINISHED"}


class GPP_OT_RemovePalette(Operator):
    bl_idname = "gpp.remove_palette"
    bl_label = "Remove Palette"
    bl_description = "Remove the active palette (at least one must remain)"

    def execute(self, context):
        props = context.scene.gpp_props
        if len(props.palettes) <= 1:
            self.report({"WARNING"}, "Cannot remove the last palette")
            return {"CANCELLED"}
        props.palettes.remove(props.active_palette_index)
        props.active_palette_index = max(0, props.active_palette_index - 1)
        return {"FINISHED"}


class GPP_OT_DuplicatePalette(Operator):
    bl_idname = "gpp.duplicate_palette"
    bl_label = "Duplicate Palette"
    bl_description = "Duplicate the active palette"

    def execute(self, context):
        props = context.scene.gpp_props
        src = _current_palette(props)
        if src is None:
            return {"CANCELLED"}
        dst = props.palettes.add()
        dst.name = src.name + " Copy"
        for e in src.entries:
            ne = dst.entries.add()
            ne.label = e.label
            ne.display_color = e.display_color[:]
            ne.grayscale_value = e.grayscale_value
        dst.active_index = src.active_index
        props.active_palette_index = len(props.palettes) - 1
        return {"FINISHED"}


class GPP_OT_MovePaletteUp(Operator):
    bl_idname = "gpp.move_palette_up"
    bl_label = "Move Palette Up"
    bl_description = "Move the active palette one slot up"

    def execute(self, context):
        props = context.scene.gpp_props
        idx = props.active_palette_index
        if idx <= 0:
            return {"CANCELLED"}
        props.palettes.move(idx, idx - 1)
        props.active_palette_index = idx - 1
        return {"FINISHED"}


class GPP_OT_MovePaletteDown(Operator):
    bl_idname = "gpp.move_palette_down"
    bl_label = "Move Palette Down"
    bl_description = "Move the active palette one slot down"

    def execute(self, context):
        props = context.scene.gpp_props
        idx = props.active_palette_index
        if idx >= len(props.palettes) - 1:
            return {"CANCELLED"}
        props.palettes.move(idx, idx + 1)
        props.active_palette_index = idx + 1
        return {"FINISHED"}


class GPP_OT_ExportPalettes(Operator):
    bl_idname = "gpp.export_palettes"
    bl_label = "Export Palettes (.pal)"
    bl_description = "Export all palettes to a .pal file (JSON)"

    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.pal", options={"HIDDEN"})
    filename_ext = ".pal"

    def invoke(self, context, event):
        self.filepath = "palettes.pal"
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        import os
        props = context.scene.gpp_props

        fp = self.filepath
        if not fp.lower().endswith(".pal"):
            fp += ".pal"

        pattern_texture_path = ""
        if props.painted_image and props.painted_image.filepath:
            abs_img = bpy.path.abspath(props.painted_image.filepath)
            if os.path.isfile(abs_img):
                pal_dir = os.path.dirname(os.path.abspath(fp))
                try:
                    pattern_texture_path = (
                        os.path.relpath(abs_img, pal_dir).replace("\\", "/")
                    )
                except ValueError:
                    pattern_texture_path = abs_img.replace("\\", "/")

        data = {
            "version": "1.0",
            "pattern_texture": pattern_texture_path,
            "palettes": [
                {
                    "name": pal.name,
                    "entries": [
                        {
                            "label": e.label,
                            "display_color": list(e.display_color),
                            "grayscale_value": e.grayscale_value,
                        }
                        for e in pal.entries
                    ],
                }
                for pal in props.palettes
            ],
        }
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self.report({"INFO"}, f"Exported {len(props.palettes)} palette(s) -> {fp}")
        return {"FINISHED"}


class GPP_OT_ImportPalettes(Operator):
    bl_idname = "gpp.import_palettes"
    bl_label = "Import Palettes (.pal)"
    bl_description = "Import palettes from a .pal file (appends to existing palettes)"

    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.pal", options={"HIDDEN"})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        props = context.scene.gpp_props
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            self.report({"ERROR"}, f"Could not read file: {exc}")
            return {"CANCELLED"}

        imported = 0
        for pal_data in data.get("palettes", []):
            pal = props.palettes.add()
            pal.name = pal_data.get("name", "Imported")
            for ed in pal_data.get("entries", []):
                e = pal.entries.add()
                e.label = ed.get("label", "Swatch")
                c = ed.get("display_color", [1.0, 1.0, 1.0])
                e.display_color = (float(c[0]), float(c[1]), float(c[2]))
                e.grayscale_value = float(ed.get("grayscale_value", 0.0))
            imported += 1

        if imported > 0:
            props.active_palette_index = len(props.palettes) - 1
        self.report({"INFO"}, f"Imported {imported} palette(s) from {self.filepath}")
        return {"FINISHED"}


class GPP_OT_BakeLUT(Operator):
    bl_idname = "gpp.bake_lut"
    bl_label = "Bake Palette LUT"
    bl_description = "Generate a 256x1 colour-lookup image from the active palette"

    def execute(self, context):
        props = context.scene.gpp_props
        pal = _current_palette(props)
        if pal is None or len(pal.entries) == 0:
            self.report({"WARNING"}, "Active palette is empty")
            return {"CANCELLED"}
        _bake_lut_now(props)
        self.report({"INFO"}, f"LUT '{props.lut_image_name}' baked ({len(pal.entries)} entries)")
        return {"FINISHED"}


class GPP_OT_BakeColorTexture(Operator):
    bl_idname = "gpp.bake_color_texture"
    bl_label = "Bake Color Texture"
    bl_description = "Replace every grayscale pixel with its palette display colour"

    def execute(self, context):
        props = context.scene.gpp_props
        pal = _current_palette(props)

        painted_img = props.painted_image
        if painted_img is None:
            self.report({"WARNING"}, "No painted texture selected")
            return {"CANCELLED"}
        if pal is None or len(pal.entries) == 0:
            self.report({"WARNING"}, "Active palette is empty")
            return {"CANCELLED"}

        entries = sorted(
            [(e.grayscale_value, tuple(e.display_color)) for e in pal.entries],
            key=lambda x: x[0],
        )
        gray_vals = np.array([e[0] for e in entries], dtype=np.float32)
        colors    = np.array([e[1] for e in entries], dtype=np.float32)

        width, height = painted_img.size
        src = np.array(painted_img.pixels[:], dtype=np.float32).reshape(height * width, 4)
        gray = src[:, 0]
        nearest = np.argmin(np.abs(gray[:, None] - gray_vals[None, :]), axis=1)
        srgb = _linear_to_srgb(colors[nearest])

        out_pixels = np.empty((height * width, 4), dtype=np.float32)
        out_pixels[:, :3] = srgb
        out_pixels[:, 3]  = src[:, 3]

        out_name = props.baked_color_image_name
        out_img = bpy.data.images.get(out_name)
        if out_img is None:
            out_img = bpy.data.images.new(out_name, width=width, height=height, alpha=True)
        elif out_img.size[0] != width or out_img.size[1] != height:
            bpy.data.images.remove(out_img)
            out_img = bpy.data.images.new(out_name, width=width, height=height, alpha=True)

        out_img.colorspace_settings.name = "sRGB"
        out_img.pixels[:] = out_pixels.ravel().tolist()
        out_img.update()
        self.report({"INFO"}, f"Baked '{out_name}' ({width}x{height})")
        return {"FINISHED"}


class GPP_OT_SetupMaterial(Operator):
    bl_idname = "gpp.setup_material"
    bl_label = "Setup / Apply Material"
    bl_description = "Build the LUT-driven material and apply it to the active object"

    def execute(self, context):
        props = context.scene.gpp_props
        painted_img = props.painted_image
        if painted_img is None:
            self.report({"WARNING"}, "Set 'Painted Texture' first")
            return {"CANCELLED"}
        lut_img = bpy.data.images.get(props.lut_image_name)
        if lut_img is None:
            self.report({"WARNING"}, "Run 'Bake Palette LUT' first")
            return {"CANCELLED"}

        mat_name = props.material_name
        mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        out   = nodes.new("ShaderNodeOutputMaterial"); out.location   = ( 600, 0)
        bsdf  = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location  = ( 300, 0)
        links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

        lut_n = nodes.new("ShaderNodeTexImage");       lut_n.location = (-100, 0)
        lut_n.image = lut_img
        lut_n.interpolation = "Closest"
        lut_n.extension = "EXTEND"
        links.new(lut_n.outputs["Color"], bsdf.inputs["Base Color"])

        cxyz  = nodes.new("ShaderNodeCombineXYZ");     cxyz.location  = (-400, 0)
        cxyz.inputs["Y"].default_value = 0.5
        cxyz.inputs["Z"].default_value = 0.0
        links.new(cxyz.outputs["Vector"], lut_n.inputs["Vector"])

        sep   = nodes.new("ShaderNodeSeparateColor");  sep.location   = (-700, 0)
        links.new(sep.outputs["Red"], cxyz.inputs["X"])

        paint_n = nodes.new("ShaderNodeTexImage");     paint_n.location = (-1050, 0)
        paint_n.image = painted_img
        paint_n.interpolation = "Closest"
        painted_img.colorspace_settings.name = "Non-Color"
        links.new(paint_n.outputs["Color"], sep.inputs[0])

        uv_n  = nodes.new("ShaderNodeUVMap");          uv_n.location  = (-1350, 0)
        links.new(uv_n.outputs["UV"], paint_n.inputs["Vector"])

        obj = context.active_object
        if obj and obj.type == "MESH":
            if mat_name not in [s.material.name for s in obj.material_slots if s.material]:
                if len(obj.material_slots) == 0:
                    obj.data.materials.append(mat)
                else:
                    obj.material_slots[0].material = mat
            self.report({"INFO"}, f"'{mat_name}' applied to '{obj.name}'")
        else:
            self.report({"INFO"}, f"'{mat_name}' created (select a mesh to assign)")
        return {"FINISHED"}


# ============================================================================
# PALETTE CREATOR — UI List
# ============================================================================

class GPP_UL_PaletteList(UIList):
    bl_idname = "GPP_UL_palette_list"

    def draw_item(self, context, layout, data, item, icon,
                  active_data, active_propname, index):
        if self.layout_type in {"DEFAULT", "COMPACT"}:
            layout.prop(item, "name", text="", emboss=False, icon="PRESET")
        else:
            layout.alignment = "CENTER"
            layout.label(text="", icon="PRESET")


# ============================================================================
# PALETTE CREATOR — Panel (Shell Fur Tool tab)
# ============================================================================

class GPP_PT_PalettePanel(Panel):
    bl_label = "Palette Creator"
    bl_idname = "GPP_PT_palette_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Shell Fur Tool"
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        props = context.scene.gpp_props

        # Palette list
        box = layout.box()
        box.label(text="Palettes", icon="PRESET")
        row = box.row()
        row.template_list(
            "GPP_UL_palette_list", "",
            props, "palettes",
            props, "active_palette_index",
            rows=3,
        )
        col = row.column(align=True)
        col.operator("gpp.add_palette",       text="", icon="ADD")
        col.operator("gpp.remove_palette",    text="", icon="REMOVE")
        col.separator()
        col.operator("gpp.duplicate_palette", text="", icon="DUPLICATE")
        col.separator()
        col.operator("gpp.move_palette_up",   text="", icon="TRIA_UP")
        col.operator("gpp.move_palette_down", text="", icon="TRIA_DOWN")
        col.separator()
        col.operator("gpp.export_palettes",   text="", icon="EXPORT")
        col.operator("gpp.import_palettes",   text="", icon="IMPORT")

        pal = _current_palette(props)
        if pal is None:
            layout.label(text="No palette — click + to add one", icon="INFO")
            return

        layout.separator()

        # Swatch grid
        if len(pal.entries) == 0:
            layout.label(text="Palette is empty.", icon="INFO")
        else:
            cols = max(1, props.columns)
            grid = layout.grid_flow(
                row_major=True, columns=cols,
                even_columns=True, even_rows=True, align=True,
            )
            for i, entry in enumerate(pal.entries):
                col = grid.column(align=True)
                op = col.operator(
                    "gpp.select_entry",
                    text=entry.label,
                    depress=(i == pal.active_index),
                )
                op.index = i
                cr = col.row()
                cr.scale_y = 1.5
                cr.prop(entry, "display_color", text="")
                if props.show_grayscale_value:
                    vr = col.row()
                    vr.alignment = "CENTER"
                    vr.label(text=f"{entry.grayscale_value:.3f}")

        layout.separator()

        # Active entry editor
        if len(pal.entries) > 0 and pal.active_index < len(pal.entries):
            active = pal.entries[pal.active_index]
            box = layout.box()
            box.label(text=f"Edit: {active.label}", icon="BRUSH_DATA")
            box.prop(active, "label",           text="Name")
            box.prop(active, "display_color",   text="Display Color")
            box.prop(active, "grayscale_value", text="Grayscale Value")

        layout.separator()

        # Entry management
        row = layout.row(align=True)
        row.operator("gpp.add_entry",    text="",               icon="ADD")
        row.operator("gpp.remove_entry", text="",               icon="REMOVE")
        row.operator("gpp.init_palette", text="Reset Defaults", icon="FILE_REFRESH")

        layout.separator()

        # LUT & Material
        box = layout.box()
        box.label(text="Color LUT & Material", icon="MATERIAL")
        box.prop(props, "painted_image",  text="Painted Texture")
        box.prop(props, "lut_image_name", text="LUT Name")
        box.prop(props, "material_name",  text="Material Name")
        row = box.row(align=True)
        row.operator("gpp.bake_lut",       text="Bake Palette LUT",      icon="IMAGE_DATA")
        row.operator("gpp.setup_material", text="Setup / Apply Material", icon="NODETREE")
        lut_img = bpy.data.images.get(props.lut_image_name)
        if lut_img:
            box.template_preview(lut_img)

        # Bake Color Texture
        box2 = layout.box()
        box2.label(text="Bake Color Texture", icon="RENDER_RESULT")
        box2.prop(props, "baked_color_image_name", text="Output Name")
        box2.operator("gpp.bake_color_texture", text="Bake Color Texture", icon="IMAGE_RGB")
        baked_img = bpy.data.images.get(props.baked_color_image_name)
        if baked_img:
            box2.template_preview(baked_img)


# ============================================================================
# SHELL FUR TOOL — Panel
# ============================================================================

class VIEW3D_PT_my_custom_panel(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Shell Fur Tool"
    bl_label = "Shell Fur Settings"
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        gpp = context.scene.gpp_props

        row = layout.row()
        row.prop_search(context.scene, "pinata_object", bpy.data, "objects", text="Object")

        # Palette colour source (quick reference — full controls in Palette Creator panel below)
        box = layout.box()
        box.label(text="Palette Colour Source", icon="MATERIAL")
        box.prop(gpp, "painted_image", text="Painted Texture")
        box.prop(gpp, "lut_image_name", text="LUT Image")
        row2 = box.row(align=True)
        row2.operator("gpp.bake_lut", text="Bake LUT", icon="IMAGE_DATA")
        box.label(text="Configure colours in the Palette Creator panel below", icon="INFO")

        row = layout.row()
        row.prop(context.scene, "pinata_color_uv_map", text="Color UV Map")

        row = layout.row()
        row.prop(context.scene, "pinata_texture2", text="Mask")
        row = layout.row()
        row.prop(context.scene, "pinata_texture3", text="Fur Shape")
        row = layout.row()
        row.prop(context.scene, "pinata_shape_lerp", text="Shape Heightmap")

        row = layout.row()
        row.prop(context.scene, "pinata_uv_map", text="Fur UV Map")

        row = layout.row()
        row.prop(context.scene, "pinata_fur_density", text="Fur Density")
        row = layout.row()
        row.prop(context.scene, "pinata_fur_resolution", text="Fur Resolution")
        row = layout.row()
        row.prop(context.scene, "pinata_fur_length", text="Fur Length")
        row = layout.row()
        row.prop(context.scene, "pinata_fur_height", text="Fur Height")
        row = layout.row()
        row.prop(context.scene, "pinata_fur_shade", text="Fur Shade")
        row = layout.row()
        row.prop(context.scene, "pinata_fur_index", text="Material Index")
        row = layout.row()
        row.prop(context.scene, "pinata_fur_am", text="Apply Modifier")

        row = layout.row()
        row.operator("object.rebuild_fur", text="Rebuild Fur")
        row = layout.row()
        row.operator("object.delete_fur", text="Delete Fur")


# ============================================================================
# SHELL FUR TOOL — Rebuild Fur Operator
# ============================================================================

class OPERATOR_OT_rebuild_fur(bpy.types.Operator):
    bl_idname = "object.rebuild_fur"
    bl_label = "Rebuild Fur"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if context.scene.pinata_object is None:
            self.report({"ERROR"}, "Select an object in the 'Object' field first")
            return {"CANCELLED"}
        if context.scene.pinata_texture2 is None:
            self.report({"ERROR"}, "Select a Mask texture first")
            return {"CANCELLED"}
        if context.scene.pinata_texture3 is None:
            self.report({"ERROR"}, "Select a Fur Shape texture first")
            return {"CANCELLED"}
        gpp               = context.scene.gpp_props
        Height            = context.scene.pinata_fur_height
        ShellCount        = context.scene.pinata_fur_resolution
        PinataName        = context.scene.pinata_object.name
        FurMaskTexture    = context.scene.pinata_texture2.name
        FurPatternTexture = context.scene.pinata_texture3.name
        ShapeLerp         = context.scene.pinata_shape_lerp
        Shade             = context.scene.pinata_fur_shade
        FurSize           = context.scene.pinata_fur_density
        FurLength         = context.scene.pinata_fur_length
        UVMAPNAME         = context.scene.pinata_uv_map
        ColorUVMapName    = context.scene.pinata_color_uv_map

        # Validate palette colour source
        painted_img = gpp.painted_image
        if painted_img is None:
            self.report({"ERROR"}, "Set 'Painted Texture' in the Palette Creator panel first")
            return {"CANCELLED"}

        lut_img = bpy.data.images.get(gpp.lut_image_name)
        if lut_img is None:
            self.report({"WARNING"}, "LUT not found — baking from active palette")
            _bake_lut_now(gpp)
            lut_img = bpy.data.images.get(gpp.lut_image_name)
            if lut_img is None:
                self.report({"ERROR"}, "Failed to bake LUT. Configure the Palette Creator first.")
                return {"CANCELLED"}

        # Delete existing fur shells for this object
        for obj in context.scene.objects:
            if obj.name.startswith(f"{PinataName}FurShell"):
                bpy.data.objects.remove(obj, do_unlink=True)

        # Create or reuse the FurMask material (fully transparent placeholder)
        maskmat = bpy.data.materials.get("FurMask")
        if maskmat is None:
            maskmat = bpy.data.materials.new(name="FurMask")
            maskmat.use_nodes = True
            node_tree = maskmat.node_tree
            nodes = node_tree.nodes
            bsdf = nodes.get("Principled BSDF")
            assert bsdf
            # Blender 5.1: BLENDED enables proper alpha blending
            maskmat.surface_render_method = "BLENDED"
            alphavalue = nodes.new(type="ShaderNodeValue")
            alphavalue.outputs[0].default_value = 0.0
            alphavalue.location.x = -300
            alphavalue.location.y = 0
            node_tree.links.new(alphavalue.outputs[0], bsdf.inputs["Alpha"])

        for i in range(ShellCount):
            obj_copy = context.scene.pinata_object.copy()
            obj_copy.data = context.scene.pinata_object.data.copy()
            context.collection.objects.link(obj_copy)
            a = i + 1

            if i > 0:
                modifier = obj_copy.modifiers.new("Displace", "DISPLACE")
                modifier.strength = Height * i
                if context.scene.pinata_fur_am:
                    context.view_layer.objects.active = obj_copy
                    bpy.ops.object.modifier_apply(modifier="Displace")

            obj_copy.name = f"{PinataName}FurShell{a}"
            bpy.data.objects[obj_copy.name].hide_select = True

            # Remove stale material from a previous build
            old_mat = bpy.data.materials.get(f"{PinataName}_FurShell_{a}")
            if old_mat:
                bpy.data.materials.remove(old_mat)

            mat = bpy.data.materials.new(name=f"{PinataName}_FurShell_{a}")
            mat.use_nodes = True
            node_tree = mat.node_tree
            nodes = node_tree.nodes
            links = node_tree.links
            bsdf = nodes.get("Principled BSDF")
            assert bsdf

            # ── Palette-driven colour chain ───────────────────────────────────
            # Sample the grayscale painted texture and look up the palette LUT
            # to produce the final display colour for this pixel.

            color_uvnode = nodes.new(type="ShaderNodeUVMap")
            color_uvnode.uv_map = ColorUVMapName
            color_uvnode.location = (-1600, 300)

            paint_node = nodes.new(type="ShaderNodeTexImage")
            paint_node.image = painted_img
            paint_node.interpolation = "Closest"
            paint_node.location = (-1300, 300)
            painted_img.colorspace_settings.name = "Non-Color"
            links.new(color_uvnode.outputs["UV"], paint_node.inputs["Vector"])

            # Extract R channel (equals grayscale value)
            sep_node = nodes.new(type="ShaderNodeSeparateColor")
            sep_node.location = (-1000, 300)
            links.new(paint_node.outputs["Color"], sep_node.inputs[0])

            # Build 1-D UV for LUT lookup (U = grayscale, V = 0.5)
            cxyz_node = nodes.new(type="ShaderNodeCombineXYZ")
            cxyz_node.inputs["Y"].default_value = 0.5
            cxyz_node.inputs["Z"].default_value = 0.0
            cxyz_node.location = (-800, 300)
            links.new(sep_node.outputs["Red"], cxyz_node.inputs["X"])

            lut_node = nodes.new(type="ShaderNodeTexImage")
            lut_node.image = lut_img
            lut_node.interpolation = "Closest"
            lut_node.extension = "EXTEND"
            lut_node.location = (-600, 300)
            links.new(cxyz_node.outputs["Vector"], lut_node.inputs["Vector"])

            # ── Shading chain (tip-to-root darkening) ─────────────────────────

            shadenode = nodes.new(type="ShaderNodeVectorMath")
            shadenode.operation = "MULTIPLY"
            shadenode.location = (-350, 200)

            shadevalue = nodes.new(type="ShaderNodeValue")
            shadevalue.outputs[0].default_value = Shade
            shadevalue.location = (-550, 100)

            rvalue = nodes.new(type="ShaderNodeValue")
            rvalue.outputs[0].default_value = 1.0
            rvalue.location = (0, 400)

            layervalue = nodes.new(type="ShaderNodeValue")
            layervalue.outputs[0].default_value = a / ShellCount
            layervalue.location = (-350, 100)

            mixshadenode = nodes.new(type="ShaderNodeMix")
            mixshadenode.data_type = "RGBA"
            mixshadenode.location = (0, 200)

            furmnode = nodes.new(type="ShaderNodeTexImage")
            furmnode.image = bpy.data.images[FurMaskTexture]
            furmnode.location = (-1300, -300)

            links.new(lut_node.outputs["Color"], shadenode.inputs[0])
            links.new(shadevalue.outputs[0],     shadenode.inputs[1])
            links.new(rvalue.outputs[0],         bsdf.inputs["Roughness"])
            links.new(layervalue.outputs[0],     mixshadenode.inputs[0])

            if i == 0:
                # Base shell: blend between shaded colour and original,
                # modulated by the fur mask texture.
                mixmshadenode = nodes.new(type="ShaderNodeMix")
                mixmshadenode.data_type = "RGBA"
                mixmshadenode.location = (-150, 300)

                links.new(shadenode.outputs["Vector"],     mixmshadenode.inputs["A"])
                links.new(lut_node.outputs["Color"],       mixmshadenode.inputs["B"])
                links.new(furmnode.outputs[0],             mixmshadenode.inputs[0])
                links.new(mixmshadenode.outputs["Result"], mixshadenode.inputs["A"])
                links.new(lut_node.outputs["Color"],       mixshadenode.inputs["B"])
                links.new(mixshadenode.outputs["Result"],  bsdf.inputs["Base Color"])

                # Blender 5.1: DITHERED = alpha clip / cutout rendering
                mat.surface_render_method = "DITHERED"

            else:
                links.new(shadenode.outputs["Vector"],    mixshadenode.inputs["A"])
                links.new(lut_node.outputs["Color"],      mixshadenode.inputs["B"])
                links.new(mixshadenode.outputs["Result"], bsdf.inputs["Base Color"])

                # ── Fur pattern / alpha chain ─────────────────────────────────

                furpnode = nodes.new(type="ShaderNodeTexImage")
                furpnode.image = bpy.data.images[FurPatternTexture]
                furpnode.location = (-1300, -600)

                alpha_mult_node = nodes.new(type="ShaderNodeMath")
                alpha_mult_node.operation = "MULTIPLY"
                alpha_mult_node.location = (0, -600)

                uvaddnode = nodes.new(type="ShaderNodeVectorMath")
                uvaddnode.operation = "ADD"
                uvaddnode.location = (-1400, -600)

                # Mix node drives the per-layer Y UV offset (fur lean / direction)
                mixuvnode = nodes.new(type="ShaderNodeMix")
                mixuvnode.data_type = "VECTOR"
                mixuvnode.location = (-1600, -600)
                mixuvnode.inputs[5].default_value[1] = FurLength   # B.Y = lean amount
                mixuvnode.inputs[0].default_value = a / ShellCount  # Factor = layer depth

                uvmultnode = nodes.new(type="ShaderNodeVectorMath")
                uvmultnode.operation = "MULTIPLY"
                uvmultnode.location = (-1800, -300)

                uvnode = nodes.new(type="ShaderNodeUVMap")
                uvnode.uv_map = UVMAPNAME
                uvnode.location = (-2000, -300)

                sizevalue = nodes.new(type="ShaderNodeValue")
                sizevalue.outputs[0].default_value = FurSize
                sizevalue.location = (-2000, -500)

                mixalphanode = nodes.new(type="ShaderNodeMix")
                mixalphanode.data_type = "FLOAT"
                mixalphanode.location = (-200, -450)

                links.new(uvnode.outputs["UV"],   uvmultnode.inputs[0])
                links.new(sizevalue.outputs[0],   uvmultnode.inputs[1])
                links.new(uvmultnode.outputs[0],  uvaddnode.inputs[0])
                links.new(mixuvnode.outputs[1],   uvaddnode.inputs[1])
                links.new(uvaddnode.outputs[0],   furpnode.inputs[0])
                links.new(furmnode.outputs[0],    mixalphanode.inputs[0])
                links.new(furpnode.outputs[1],    mixalphanode.inputs[2])

                # Shape heightmap step function: floor(clamp(colour * 16 / layer))
                mult_node = nodes.new(type="ShaderNodeMath")
                mult_node.operation = "MULTIPLY"
                mult_node.inputs[1].default_value = 16.0
                mult_node.location = (200, -700)

                div_node = nodes.new(type="ShaderNodeMath")
                div_node.operation = "DIVIDE"
                div_node.inputs[1].default_value = float(a)
                div_node.location = (400, -700)

                floor_node = nodes.new(type="ShaderNodeMath")
                floor_node.operation = "FLOOR"
                floor_node.location = (600, -700)

                clamp_node = nodes.new(type="ShaderNodeClamp")
                clamp_node.inputs["Min"].default_value = 0.0
                clamp_node.inputs["Max"].default_value = 1.0
                clamp_node.location = (800, -700)

                if ShapeLerp:
                    links.new(furpnode.outputs[0],            mult_node.inputs[0])
                    links.new(mult_node.outputs[0],           div_node.inputs[0])
                    links.new(div_node.outputs[0],            floor_node.inputs[0])
                    links.new(floor_node.outputs[0],          clamp_node.inputs["Value"])
                    links.new(mixalphanode.outputs["Result"], alpha_mult_node.inputs[0])
                    links.new(clamp_node.outputs["Result"],   alpha_mult_node.inputs[1])
                    links.new(alpha_mult_node.outputs[0],     bsdf.inputs["Alpha"])
                else:
                    links.new(mixalphanode.outputs["Result"], bsdf.inputs["Alpha"])

                # Blender 5.1: DITHERED = alpha clip / cutout rendering
                mat.surface_render_method = "DITHERED"

            # Assign material to the correct slot; fill all other slots with maskmat
            if obj_copy.data.materials:
                obj_copy.data.materials[context.scene.pinata_fur_index] = mat
            else:
                obj_copy.data.materials.append(mat)

            for slot_idx, amaterial in enumerate(obj_copy.data.materials):
                if amaterial != mat:
                    obj_copy.data.materials[slot_idx] = maskmat

        return {"FINISHED"}


# ============================================================================
# SHELL FUR TOOL — Delete Fur Operator
# ============================================================================

class OPERATOR_OT_delete_fur(bpy.types.Operator):
    bl_idname = "object.delete_fur"
    bl_label = "Delete Fur"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        if context.scene.pinata_object is None:
            self.report({"ERROR"}, "Select an object in the 'Object' field first")
            return {"CANCELLED"}
        PinataName = context.scene.pinata_object.name
        for obj in context.scene.objects:
            if obj.name.startswith(f"{PinataName}FurShell"):
                bpy.data.objects.remove(obj, do_unlink=True)
        return {"FINISHED"}


# ============================================================================
# Registration
# ============================================================================

_PALETTE_CLASSES = [
    GPP_PaletteEntry,
    GPP_Palette,
    GPP_SceneProps,
    GPP_OT_InitPalette,
    GPP_OT_AddEntry,
    GPP_OT_RemoveEntry,
    GPP_OT_SelectEntry,
    GPP_OT_PaintStamp,
    GPP_OT_AddPalette,
    GPP_OT_RemovePalette,
    GPP_OT_DuplicatePalette,
    GPP_OT_MovePaletteUp,
    GPP_OT_MovePaletteDown,
    GPP_OT_ExportPalettes,
    GPP_OT_ImportPalettes,
    GPP_OT_BakeLUT,
    GPP_OT_BakeColorTexture,
    GPP_OT_SetupMaterial,
    GPP_UL_PaletteList,
    GPP_PT_PalettePanel,
]

_FUR_CLASSES = [
    VIEW3D_PT_my_custom_panel,
    OPERATOR_OT_rebuild_fur,
    OPERATOR_OT_delete_fur,
]


@bpy.app.handlers.persistent
def _gpp_load_post(filepath):
    for scene in bpy.data.scenes:
        _ensure_palettes(scene.gpp_props)


def register():
    for cls in _PALETTE_CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.gpp_props = bpy.props.PointerProperty(type=GPP_SceneProps)
    bpy.app.handlers.load_post.append(_gpp_load_post)

    def _deferred_init():
        for scene in bpy.data.scenes:
            _ensure_palettes(scene.gpp_props)
        return None

    bpy.app.timers.register(_deferred_init, first_interval=0.0)

    for cls in _FUR_CLASSES:
        bpy.utils.register_class(cls)

    bpy.types.Scene.pinata_object = bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="Pinata Body",
        description="Select the object to put fur on",
    )
    bpy.types.Scene.pinata_texture2 = bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Mask Texture",
        description="Anything black is visible",
    )
    bpy.types.Scene.pinata_texture3 = bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Fur Shape Texture",
        description="A texture to define the shape of the fur",
    )
    bpy.types.Scene.pinata_shape_lerp = bpy.props.BoolProperty(
        name="Use Shape Heightmap",
        description="Shape the fur using a height map on the fur shape texture (for pointy fur)",
        default=False,
    )
    bpy.types.Scene.pinata_uv_map = bpy.props.StringProperty(
        name="Fur UV Map",
        description="UV map used for fur pattern tiling and direction",
        default="UVMap",
    )
    bpy.types.Scene.pinata_color_uv_map = bpy.props.StringProperty(
        name="Color UV Map",
        description="UV map used to sample the palette painted texture",
        default="UVMap",
    )
    bpy.types.Scene.pinata_fur_shade = bpy.props.FloatProperty(
        name="Fur Shade",
        description="Darkening applied at the base of each fur shell",
        default=0.1,
        min=0.0,
        max=1.0,
        step=0.1,
    )
    bpy.types.Scene.pinata_fur_density = bpy.props.IntProperty(
        name="Fur Density",
        description="UV scale of the fur pattern",
        default=5,
        min=-100,
        max=100,
        step=1,
    )
    bpy.types.Scene.pinata_fur_resolution = bpy.props.IntProperty(
        name="Fur Resolution",
        description="Number of fur shells (more = smoother but heavier)",
        default=16,
        min=8,
        max=64,
        step=1,
    )
    bpy.types.Scene.pinata_fur_length = bpy.props.FloatProperty(
        name="Fur Length",
        description="Fur lean / direction. 0 = straight, 0.15 suits most cases",
        default=0.15,
        min=-1.0,
        max=1.0,
        step=0.01,
    )
    bpy.types.Scene.pinata_fur_height = bpy.props.FloatProperty(
        name="Fur Height",
        description="Gap between shells; lower = shorter / tighter fur",
        default=0.015,
        min=-1.0,
        max=1.0,
        step=0.01,
    )
    bpy.types.Scene.pinata_fur_index = bpy.props.IntProperty(
        name="Material Index",
        description="Material slot index to apply the fur to",
        default=0,
        min=0,
        max=100,
        step=1,
    )
    bpy.types.Scene.pinata_fur_am = bpy.props.BoolProperty(
        name="Apply Modifier",
        description="Apply the displace modifier to each shell after creation",
    )


def unregister():
    if _gpp_load_post in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_gpp_load_post)

    for cls in reversed(_PALETTE_CLASSES):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.gpp_props

    for cls in reversed(_FUR_CLASSES):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.pinata_object
    del bpy.types.Scene.pinata_texture2
    del bpy.types.Scene.pinata_texture3
    del bpy.types.Scene.pinata_shape_lerp
    del bpy.types.Scene.pinata_uv_map
    del bpy.types.Scene.pinata_color_uv_map
    del bpy.types.Scene.pinata_fur_density
    del bpy.types.Scene.pinata_fur_resolution
    del bpy.types.Scene.pinata_fur_length
    del bpy.types.Scene.pinata_fur_height
    del bpy.types.Scene.pinata_fur_shade
    del bpy.types.Scene.pinata_fur_index
    del bpy.types.Scene.pinata_fur_am


if __name__ == "__main__":
    register()