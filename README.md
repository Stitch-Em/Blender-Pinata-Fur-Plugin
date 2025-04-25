# Blender Pinata Fur Plugin
 Adds Shell Fur to your Pinatas in Blender!

![image](https://github.com/user-attachments/assets/87aaa9db-4357-4508-8281-e48675d880e0)

---

# How to set up

 - First you have to add the plugin to your addons

![image](https://github.com/user-attachments/assets/2a2c2b80-82f5-497d-b37f-5c98aa50dfff)


 - Then you click the viewport toolbar arrow to see the fur menu

![image](https://github.com/user-attachments/assets/4d11962e-f2a2-4562-9fa8-ad3a8616bfaf)

 - Once you see the fur menu you can adjust the settings

![image](https://github.com/user-attachments/assets/524b32d1-b5fa-4ad7-9c26-961f877a3d89)

 - **Object**: The object you want to add fur too
 - **Color**: The color texture for your object
 - **Mask**: The Mask is a texture that masks out any part thats painted white so you can add eyeholes or keep the fur from being visible in the mouth
 - **Fur Shape**: This is the cutout for the shape of the fur, the ones bundled with the zip are a regular pinata "Land" and scales for sea pinata "Sea"
 - **Shape Heightmap**: Uses the brightness of the shape to control the mask based on the layer, If the shape has the brightness of 1 that would showup on the last layer
 - **UV Map**: This allows you to set the name of the UV Map to use for the fur, This gives you more freedom to move the fur around without redrawing the color texture (UV channel needs to be created first)

---

 - **Fur Density**: Changes how big the fur is on the object, The larger the number the smaller the fur will be
 - **Fur Resolution**: Increases the number of shell layers that get generated, the more you add the more your blender will lag, 16 is usually good enough
 - **Fur Length**: will control the angle the fur points, The lower the number the more straight up the fur will look
 - **Fur Shade**: Controls how dark the base of the fur is to give it more depth

---

 - **Material Index**: If your model has more then one material then using the material index will allow you to select which material to render the fur on
 - **Apply Modifier**: Its generally not recommended to export with the fur due to the poor optimization of the mesh, The fur should be done with geometry shader, However this option is here in case you need to apply the modifiers.

---

 - You may want to delete the fur before rebuilding to make sure you dont get any issues with the material

