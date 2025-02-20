from chemvista.scene_objects import SceneManager
import pathlib

# Initialize scene manager
scene = SceneManager()

# Load test files
data_dir = pathlib.Path(__file__).parent.parent / 'tests' / 'data'
mol_file = data_dir / 'mpf_motor.xyz'
cube_file = data_dir / 'C2H4.eldens.cube'

# Load molecule from XYZ
mol_name = scene.load_molecule(mol_file)

# Update its settings
mol_obj = scene.get_object_by_name(mol_name)
mol_obj.render_settings.show_hydrogens = False
mol_obj.render_settings.show_numbers = True

# Load cube file as both molecule and field
names = scene.load_molecule_from_cube(cube_file)
mol_name, field_name = names

# Update field settings
field_obj = scene.get_object_by_name(field_name)
field_obj.render_settings.color = 'red'
field_obj.render_settings.opacity = 0.5

# Render scene
plotter = scene.render()
plotter.show()
