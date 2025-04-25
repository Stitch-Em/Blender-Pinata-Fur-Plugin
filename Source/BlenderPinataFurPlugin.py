# -----------------------------------------------------------------------------------------------------------
# Author: @SolarCookies - Sebastian Robinson
# Special thanks to @Blegh for the 4.3.0 fix
# Copyright: MIT License
# Blender Version: 4.4.1
# Info: A script to generate shell based fur for pinatas or any other animal.
#
#
#-----------------------------------------------------------------------------------------------------------

bl_info = {
    "name": "Shell Fur Tool",
    "author": "SolarCookies",
    "version": (0, 1, 6),  # Updated version
    "blender": (4, 4, 1),
    "location": "3D Viewport > Sidebar > Shell Fur Tool",
    "description": "A Tool to add Shell Fur to your model",
    "category": "Graphics",
}

import bpy

class VIEW3D_PT_my_custom_panel(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Shell Fur Tool"
    bl_label = "Shell Fur Settings"

    def draw(self, context):
        """define the layout of the panel"""
        layout = self.layout

        # Object Selector as Pointer Input
        row = layout.row()
        row.prop_search(context.scene, "pinata_object", bpy.data, "objects", text="Object")

        # Texture Selectors as Image Input
        row = layout.row()
        row.prop(context.scene, "pinata_texture1", text="Color")
        row = layout.row()
        row.prop(context.scene, "pinata_texture2", text="Mask")
        row = layout.row()
        row.prop(context.scene, "pinata_texture3", text="Fur Shape")
        row = layout.row()
        row.prop(context.scene, "pinata_shape_lerp", text="Shape Heightmap")
        
        # UV Map Selector
        row = layout.row()
        row.prop(context.scene, "pinata_uv_map", text="UV Map")

        # Float Value Input
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
        
        # Buttons from the original code
        row = layout.row()
        row.operator("object.rebuild_fur", text="Rebuild Fur")
        row = layout.row()
        row.operator("object.delete_fur", text="Delete Fur")
        
        
        
class OPERATOR_OT_rebuild_fur(bpy.types.Operator):
    bl_idname = "object.rebuild_fur"
    bl_label = "Rebuild Fur"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        print("Running Fur Stuff?")
        

        Height = bpy.context.scene.pinata_fur_height
        ShellCount = bpy.context.scene.pinata_fur_resolution  
        PinataName = bpy.context.scene.pinata_object.name
        ColorTexture = bpy.context.scene.pinata_texture1.name  
        FurMaskTexture = bpy.context.scene.pinata_texture2.name  
        FurPatternTexture = bpy.context.scene.pinata_texture3.name
        ShapeLerp = bpy.context.scene.pinata_shape_lerp  
        Shade = bpy.context.scene.pinata_fur_shade
        FurSize = bpy.context.scene.pinata_fur_density
        FurLength = bpy.context.scene.pinata_fur_length
        UVMAPNAME = bpy.context.scene.pinata_uv_map
        print("Running Fur Stuff")
        # Delete existing objects with the name pattern "FurShell"
        for obj in bpy.context.scene.objects:
            if obj.name.startswith("{PinataName}FurShell"):
                bpy.data.objects.remove(obj, do_unlink=True)
                
        
                
        maskmat = bpy.data.materials.get("FurMask")
        if maskmat is None:
            # Create material
            maskmat = bpy.data.materials.new(name="FurMask")
            #
            maskmat.use_nodes = True
            node_tree = maskmat.node_tree
            nodes = node_tree.nodes
            bsdf = nodes.get("Principled BSDF")
            assert(bsdf)
                
            maskmat.blend_method  = 'BLEND'
            maskmat.surface_render_method   = 'DITHERED'
                
            alphavalue = nodes.new(type="ShaderNodeValue")
            alphavalue.outputs[0].default_value = 0.0
            alphavalue.location.x = -300      
            alphavalue.location.y = 0
                
            node_tree.links.new(alphavalue.outputs[0], bsdf.inputs["Alpha"])
            
            #empty = bpy.ops.object.empty_add(type='PLAIN_AXES', align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
            #empty.name = f"{PinataName}FurShells"
            
        for i in range(ShellCount):
            
            # Copy the active object
            obj_copy = bpy.context.scene.pinata_object.copy()

            # Remove Linked Data from the selected object
            obj_copy.data = bpy.context.scene.pinata_object.data.copy()
            
            # Adds Copy to viewport
            bpy.context.collection.objects.link(obj_copy)
            a = i + 1
            
            if i == 0:
                print("Skiping first shell modifier")
            else:    
                # Add Displace modifier and sets strength.
                modifier = obj_copy.modifiers.new('Displace', 'DISPLACE')
                x = i
                y = Height * x
                z = 0 + y # Dont use unless needed.
                modifier.strength = z
                
                if bpy.context.scene.pinata_fur_am:
                    bpy.context.view_layer.objects.active = obj_copy
                    bpy.ops.object.modifier_apply(modifier="Displace")
                
            
            # Set Name
            obj_copy.name = f"{PinataName}FurShell{a}"
            
            bpy.data.objects[obj_copy.name].hide_select = True
            
            # Find if material exist already.
            mat = bpy.data.materials.get(f"{PinataName}_FurShell_{a}")
            if mat is None:
                print('.')
            else:
                bpy.data.materials.remove(bpy.data.materials.get(f"{PinataName}_FurShell_{a}"))
                
            mat = bpy.data.materials.get(f"{PinataName}_FurShell_{a}")
            if mat is None:
                # Create material
                mat = bpy.data.materials.new(name=f"{PinataName}_FurShell_{a}")
                #
                mat.use_nodes = True
                node_tree = mat.node_tree
                nodes = node_tree.nodes
                bsdf = nodes.get("Principled BSDF")
                assert(bsdf)
                
                
                
                #-----------------------------------------------Color--------------------------------------------------#
                #add color texture
                colornode = nodes.new(type="ShaderNodeTexImage")
                colornode.image = bpy.data.images[f"{ColorTexture}"]
                colornode.location.x = -1000        
                colornode.location.y = 300 
                
                
                #add multiply for the shading
                shadenode = nodes.new(type="ShaderNodeVectorMath")
                shadenode.operation = 'MULTIPLY'
                shadenode.location.x = -600        
                shadenode.location.y = 100 
                
                
                #add value node for shade amount
                shadevalue = nodes.new(type="ShaderNodeValue")
                shadevalue.outputs[0].default_value = Shade
                shadevalue.location.x = -800        
                shadevalue.location.y = 0 
                
                #add value node for shade amount
                rvalue = nodes.new(type="ShaderNodeValue")
                rvalue.outputs[0].default_value = 1.0
                rvalue.location.x = -400        
                rvalue.location.y = 400
                
                #add value node for shade amount
                layervalue = nodes.new(type="ShaderNodeValue")
                layervalue.outputs[0].default_value = a / ShellCount
                layervalue.location.x = -600       
                layervalue.location.y = 300
                
                #Mix the color from shade to color based on the layer
                mixshadenode = nodes.new(type="ShaderNodeMix")
                mixshadenode.data_type = 'RGBA'
                mixshadenode.location.x = -250      
                mixshadenode.location.y = 300
                
                #add Fur Mask texture
                furmnode = nodes.new(type="ShaderNodeTexImage")
                furmnode.image = bpy.data.images[f"{FurMaskTexture}"]
                furmnode.location.x = -1000        
                furmnode.location.y = -300 
                
                if i == 0:
                    #Mix the color from shade to color based on the mask
                    mixmshadenode = nodes.new(type="ShaderNodeMix")
                    mixmshadenode.data_type = 'RGBA'
                    mixmshadenode.location.x = -350     
                    mixmshadenode.location.y = 300
                    
                    # make links
                    
                    node_tree.links.new(colornode.outputs[0], shadenode.inputs[0])
                    
                    node_tree.links.new(shadevalue.outputs[0], shadenode.inputs[1])
                    
                    node_tree.links.new(layervalue.outputs[0], mixshadenode.inputs[0])
                    
                    node_tree.links.new(shadenode.outputs["Vector"], mixmshadenode.inputs["A"]) 
                    
                    node_tree.links.new(colornode.outputs["Color"], mixmshadenode.inputs["B"]) 
                    
                    node_tree.links.new(furmnode.outputs[0], mixmshadenode.inputs[0])
                    
                    node_tree.links.new(mixmshadenode.outputs["Result"], mixshadenode.inputs["A"]) 
                    
                    node_tree.links.new(colornode.outputs["Color"], mixshadenode.inputs["B"])
                    
                    node_tree.links.new(mixshadenode.outputs["Result"], bsdf.inputs["Base Color"])
                    
                    node_tree.links.new(rvalue.outputs[0], bsdf.inputs["Roughness"])
                
                
                else:
                    # make links
                    
                    node_tree.links.new(colornode.outputs[0], shadenode.inputs[0])
                    
                    node_tree.links.new(shadevalue.outputs[0], shadenode.inputs[1])
                    
                    node_tree.links.new(layervalue.outputs[0], mixshadenode.inputs[0])
                    
                    node_tree.links.new(shadenode.outputs["Vector"], mixshadenode.inputs["A"])
                    
                    node_tree.links.new(colornode.outputs["Color"], mixshadenode.inputs["B"])
                    
                    node_tree.links.new(mixshadenode.outputs["Result"], bsdf.inputs["Base Color"])
                    
                    node_tree.links.new(rvalue.outputs[0], bsdf.inputs["Roughness"])
                
                if i == 0:
                    # Set Material Blend mode to alpha clip
                    mat.blend_method = 'CLIP'
                else:
                    #------------------------------------------------Mask--------------------------------------------------#
                    
                    #add Fur Pattern texture
                    furpnode = nodes.new(type="ShaderNodeTexImage")
                    furpnode.image = bpy.data.images[f"{FurPatternTexture}"]
                    furpnode.location.x = -1000        
                    furpnode.location.y = -600 
                    
                    # Multiply alpha by heightmap
                    alpha_mult_node = nodes.new(type="ShaderNodeMath")
                    alpha_mult_node.operation = 'MULTIPLY'
                    alpha_mult_node.location.x = -300
                    alpha_mult_node.location.y = -600

                    #Setup add for UV offset per layer
                    uvaddnode = nodes.new(type="ShaderNodeVectorMath")
                    uvaddnode.operation = 'ADD'
                    uvaddnode.location.x = -1200        
                    uvaddnode.location.y = -600
                    
                    
                    #Mix the color from shade to color based on the layer
                    mixuvnode = nodes.new(type="ShaderNodeMix")
                    mixuvnode.data_type = 'VECTOR'
                    mixuvnode.location.x = -1400        
                    mixuvnode.location.y = -600
                    mixuvnode.inputs[5].default_value[1] = FurLength
                    mixuvnode.inputs[0].default_value = a / ShellCount
                    
                    #Setup UV Multiply for Fur size
                    uvmultnode = nodes.new(type="ShaderNodeVectorMath")
                    uvmultnode.operation = 'MULTIPLY'
                    uvmultnode.location.x = -1400        
                    uvmultnode.location.y = -300
                    
                    # Get UV
                    # uvnode = nodes.new(type="ShaderNodeTexCoord")
                    # uvnode.location.x = -1600        
                    # uvnode.location.y = -300
                    
                    uvnode = nodes.new(type="ShaderNodeUVMap")
                    uvnode.uv_map = UVMAPNAME
                    uvnode.location.x = -1600 
                    uvnode.location.y = -300
                    
                    # Add value node for Fur Size
                    sizevalue = nodes.new(type="ShaderNodeValue")
                    sizevalue.outputs[0].default_value = FurSize
                    sizevalue.location.x = -1600       
                    sizevalue.location.y = -500
                    
                    #Mix the color from shade to color based on the layer
                    mixalphanode = nodes.new(type="ShaderNodeMix")
                    mixalphanode.data_type = 'FLOAT'
                    mixalphanode.location.x = -500     
                    mixalphanode.location.y = -450 
                    
                    # Make links
                    
                    node_tree.links.new(uvnode.outputs["UV"], uvmultnode.inputs[0])
                    node_tree.links.new(sizevalue.outputs[0], uvmultnode.inputs[1])
                    
                    node_tree.links.new(uvmultnode.outputs[0], uvaddnode.inputs[0])
                    node_tree.links.new(mixuvnode.outputs[1], uvaddnode.inputs[1])
                    
                    node_tree.links.new(uvaddnode.outputs[0], furpnode.inputs[0])
                    
                    node_tree.links.new(furmnode.outputs[0], mixalphanode.inputs[0])
                    node_tree.links.new(furpnode.outputs[1], mixalphanode.inputs[2])

                    # If heightmap option is enabled, use step function: floorclamped(((ShapeColor*16) / Layer Number))
                    
                    # Add math nodes for the step function
                    # 1. Multiply ShapeColor (furpnode.outputs[0]) by 16
                    mult_node = nodes.new(type="ShaderNodeMath")
                    mult_node.operation = 'MULTIPLY'
                    mult_node.inputs[1].default_value = 16.0
                    mult_node.location.x = -100
                    mult_node.location.y = -700

                    # 2. Divide by Layer Number (a)
                    div_node = nodes.new(type="ShaderNodeMath")
                    div_node.operation = 'DIVIDE'
                    div_node.inputs[1].default_value = float(a)
                    div_node.location.x = 100
                    div_node.location.y = -700

                    # 3. Floor
                    floor_node = nodes.new(type="ShaderNodeMath")
                    floor_node.operation = 'FLOOR'
                    floor_node.location.x = 300
                    floor_node.location.y = -700

                    # 4. Clamp (simulate floorclamped)
                    clamp_node = nodes.new(type="ShaderNodeClamp")
                    clamp_node.inputs['Min'].default_value = 0.0
                    clamp_node.inputs['Max'].default_value = 1.0
                    clamp_node.location.x = 500
                    clamp_node.location.y = -700


                    if ShapeLerp:
                        # Link the math nodes
                        node_tree.links.new(furpnode.outputs[0], mult_node.inputs[0])
                        node_tree.links.new(mult_node.outputs[0], div_node.inputs[0])
                        node_tree.links.new(div_node.outputs[0], floor_node.inputs[0])
                        node_tree.links.new(floor_node.outputs[0], clamp_node.inputs['Value'])

                        # Use the result as the alpha input
                        node_tree.links.new(mixalphanode.outputs["Result"], alpha_mult_node.inputs[0])
                        node_tree.links.new(clamp_node.outputs['Result'], alpha_mult_node.inputs[1])
                        node_tree.links.new(alpha_mult_node.outputs[0], bsdf.inputs["Alpha"])
                    else:
                        node_tree.links.new(mixalphanode.outputs["Result"], bsdf.inputs["Alpha"])
                    
                    # Set Material Blend mode to alpha clip
                    
                    mat.blend_method = 'CLIP'
                    
                    #------------------------------------------------------------------------------------------------------#
                
            # Assign material
            if obj_copy.data.materials:
                obj_copy.data.materials[bpy.context.scene.pinata_fur_index] = mat
            else:
                # no slots
                obj_copy.data.materials.append(mat)
            
            temp = 0
            for amaterial in obj_copy.data.materials:
                if amaterial != mat:
                 obj_copy.data.materials[temp] = maskmat
                 print(amaterial.name)
                 print(obj_copy.data.materials[temp].name)
                temp += 1
                
        return {'FINISHED'}
    
class OPERATOR_OT_delete_fur(bpy.types.Operator):
    bl_idname = "object.delete_fur"
    bl_label = "Delete Fur"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Delete existing objects with the name pattern "FurShell"
        for obj in bpy.context.scene.objects:
            if obj.name.startswith(f"{bpy.context.scene.pinata_object.name}FurShell"):
                bpy.data.objects.remove(obj, do_unlink=True)
                
        return {'FINISHED'}


def register():
    bpy.utils.register_class(VIEW3D_PT_my_custom_panel)
    bpy.utils.register_class(OPERATOR_OT_rebuild_fur)
    bpy.utils.register_class(OPERATOR_OT_delete_fur)
    bpy.types.Scene.pinata_object = bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="Pinata Body",
        description="Select the Object to put fur on.",
    )
    bpy.types.Scene.pinata_texture1 = bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Color Texture",
        description="Color Texture",
    )
    bpy.types.Scene.pinata_texture2 = bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Mask Texture",
        description="Anything Black is visible.",
    )
    bpy.types.Scene.pinata_texture3 = bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Fur Shape Texture",
        description="A texture to define the shape of the fur",
    )
    bpy.types.Scene.pinata_shape_lerp = bpy.props.BoolProperty(
        name="Use Shape Heightmap",
        description="Allows you to shape the fur using a height map on the fur shape texture (For pointy fur)",
        default=False,
    )
    bpy.types.Scene.pinata_uv_map = bpy.props.StringProperty(
        name="Fur UV Map",
        description="You should have UVMap 1 Be fur and UVMap 0 be color",
        default="UVMap"
    )
    bpy.types.Scene.pinata_fur_shade = bpy.props.FloatProperty(
        name="Fur Shade",
        description="Set the shade of the fur",
        default=0.1,
        min=0.0,
        max=1.0,
        step=0.1
    )
    bpy.types.Scene.pinata_fur_density = bpy.props.IntProperty(
        name="Fur Density",
        description="Set the UV Scale of the fur",
        default=5,
        min=-100,
        max=100,
        step=1
    )
    bpy.types.Scene.pinata_fur_resolution = bpy.props.IntProperty(
        name="Fur Resolution",
        description="This should stay at 16 unless you have a beeffie PC UwU",
        default=16,
        min=8,
        max=64,
        step=1
    )
    bpy.types.Scene.pinata_fur_length = bpy.props.FloatProperty(
        name="Fur Length",
        description="0 would be straight fur, 0.15 is good in most cases but you can flip it to -0.15",
        default=0.15,
        min=-1.0,
        max=1.0,
        step=0.01
    )
    bpy.types.Scene.pinata_fur_height = bpy.props.FloatProperty(
        name="Fur Height",
        description="You will have to mess with this, lower = less space between shells",
        default=0.015,
        min=-1.0,
        max=1.0,
        step=0.01
    )
    bpy.types.Scene.pinata_fur_index = bpy.props.IntProperty(
        name="Material Index",
        description="The Material to apply the fur too",
        default=0,
        min=0,
        max=100,
        step=1
    )
    bpy.types.Scene.pinata_fur_am = bpy.props.BoolProperty(
        name="Apply Modifier",
        description=""
    )


def unregister():
    bpy.utils.unregister_class(VIEW3D_PT_my_custom_panel)
    bpy.utils.unregister_class(OPERATOR_OT_rebuild_fur)
    bpy.utils.unregister_class(OPERATOR_OT_delete_fur)
    del bpy.types.Scene.pinata_object
    del bpy.types.Scene.pinata_texture1
    del bpy.types.Scene.pinata_texture2
    del bpy.types.Scene.pinata_texture3
    del bpy.types.Scene.pinata_shape_lerp
    del bpy.types.Scene.pinata_uv_map
    del bpy.types.Scene.pinata_fur_density
    del bpy.types.Scene.pinata_fur_resolution
    del bpy.types.Scene.pinata_fur_length
    del bpy.types.Scene.pinata_fur_height
    del bpy.types.Scene.pinata_fur_shade
    del bpy.types.Scene.pinata_fur_index

if __name__ == "__main__":
    register()


