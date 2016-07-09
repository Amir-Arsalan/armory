import bpy
from bpy.types import NodeTree, Node, NodeSocket
from bpy.props import *
import os
import json
import write_probes

def register():
	pass
	#bpy.utils.register_module(__name__)

def unregister():
	pass
	#bpy.utils.unregister_module(__name__)

# Generating world resources
class Object:
	def to_JSON(self):
		if bpy.data.worlds[0].CGMinimize == True:
			return json.dumps(self, default=lambda o: o.__dict__, separators=(',',':'))
		else:
			return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)

def find_node(node_group, to_node, target_socket):
	for link in node_group.links:
		if link.to_node == to_node and link.to_socket == target_socket:
			return link.from_node

def get_output_node(tree):
	for n in tree.nodes:
		if n.type == 'OUTPUT_WORLD':
			return n

def buildNodeTrees(shader_references, asset_references):
	s = bpy.data.filepath.split(os.path.sep)
	s.pop()
	fp = os.path.sep.join(s)
	os.chdir(fp)

	# Make sure Assets dir exists
	if not os.path.exists('Assets/generated/materials'):
		os.makedirs('Assets/generated/materials')
	
	# Export world nodes
	for world in bpy.data.worlds:
		buildNodeTree(world.name, world.node_tree, shader_references, asset_references)

def buildNodeTree(world_name, node_group, shader_references, asset_references):
	output = Object()
	res = Object()
	output.material_resources = [res]
	
	path = 'Assets/generated/materials/'
	material_name = world_name.replace('.', '_') + '_material'
	
	res.id = material_name
	context = Object()
	res.contexts = [context]
	context.id = 'env_map'
	context.bind_constants = []
	context.bind_textures = []
	
	bpy.data.worlds[0].world_defs = ''
	
	# Traverse world node tree
	output_node = get_output_node(node_group)
	if output_node != None:
		parse_world_output(node_group, output_node, context)
	
	# Clear to color if no texture or sky is provided
	world_defs = bpy.data.worlds[0].world_defs
	if '_EnvSky' not in world_defs and '_EnvTex' not in world_defs:
		world_defs += '_EnvCol'

	# Enable probes
	for cam in bpy.data.cameras:
		if cam.is_probe:
			bpy.data.worlds[0].world_defs += '_Probes'

	# Add resources to khafie
	dir_name = 'env_map'
	# Append world defs
	res_name = 'env_map' + world_defs
	# Reference correct shader context
	res.shader = res_name + '/' + res_name
	asset_references.append('compiled/ShaderResources/' + dir_name + '/' + res_name + '.json')
	shader_references.append('compiled/Shaders/' + dir_name + '/' + res_name)

	# Write material json
	with open(path + material_name + '.json', 'w') as f:
		f.write(output.to_JSON())

def parse_world_output(node_group, node, context):
	if node.inputs[0].is_linked:
		surface_node = find_node(node_group, node, node.inputs[0])
		parse_surface(node_group, surface_node, context)
	
def parse_surface(node_group, node, context):
	# Extract environment strength
	if node.type == 'BACKGROUND':
		bpy.data.cameras[0].world_envtex_color = node.inputs[0].default_value
		bpy.data.cameras[0].world_envtex_strength = node.inputs[1].default_value
		
		# Strength
		const = Object()
		const.id = 'envmapStrength'
		const.float = node.inputs[1].default_value
		context.bind_constants.append(const)
		
		if node.inputs[0].is_linked:
			color_node = find_node(node_group, node, node.inputs[0])
			parse_color(node_group, color_node, context)

def parse_color(node_group, node, context):		
	# Env map included
	if node.type == 'TEX_ENVIRONMENT':
		texture = Object()
		context.bind_textures.append(texture)
		texture.id = 'envmap'
		image_name =  node.image.name # With extension
		texture.name = image_name.rsplit('.', 1)[0] # Remove extension	
		# Generate prefiltered envmaps
		generate_radiance = bpy.data.worlds[0].generate_radiance
		bpy.data.cameras[0].world_envtex_name = texture.name
		disable_hdr = image_name.endswith('.jpg')
		mip_count = bpy.data.cameras[0].world_envtex_num_mips
		
		mip_count = write_probes.write_probes(image_name, disable_hdr, mip_count, generate_radiance=generate_radiance)
		
		bpy.data.cameras[0].world_envtex_num_mips = mip_count
		# Append envtex define
		bpy.data.worlds[0].world_defs += '_EnvTex'
		# Append LDR define
		if disable_hdr:
			bpy.data.worlds[0].world_defs += '_LDR'
		# Append radiance degine
		if generate_radiance:
			bpy.data.worlds[0].world_defs += '_Rad'
	
	# Append sky define
	elif node.type == 'TEX_SKY':
		bpy.data.worlds[0].world_defs += '_EnvSky'
		# Append sky properties to material
		const = Object()
		const.id = 'sunDirection'
		sun_direction = node.sun_direction
		sun_direction[1] *= -1 # Fix Y orientation
		const.vec3 = list(sun_direction)
		context.bind_constants.append(const)
		
		bpy.data.cameras[0].world_envtex_sun_direction = sun_direction
		bpy.data.cameras[0].world_envtex_turbidity = node.turbidity
		bpy.data.cameras[0].world_envtex_ground_albedo = node.ground_albedo
		
		# Irradiance json file name
		base_name = bpy.data.worlds[0].name
		bpy.data.cameras[0].world_envtex_name = base_name
		
		write_probes.write_sky_irradiance(base_name)
