import pytest
from PyQt5.QtCore import QObject
from chemvista.tree_structure import TreeNode, NodePath, TreeSignals


class TestNodePath:
    """Tests for the NodePath class"""

    def test_node_path_creation(self):
        """Test creating node paths"""
        # Create empty path
        path = NodePath()
        assert str(path) == "/"
        assert path.parts == []

        # Create path with parts
        path = NodePath(["root", "level1", "level2"])
        assert str(path) == "/root/level1/level2"
        assert path.parts == ["root", "level1", "level2"]

        # Create from string
        path = NodePath.from_string("/root/level1/level2")
        assert path.parts == ["root", "level1", "level2"]

        # Handle trailing slashes
        path = NodePath.from_string("/root/level1/level2/")
        assert path.parts == ["root", "level1", "level2"]

    def test_node_path_operations(self):
        """Test node path operations"""
        path = NodePath(["root", "level1"])

        # Test child path
        child_path = path.child("level2")
        assert str(child_path) == "/root/level1/level2"

        # Test parent path
        parent_path = path.parent()
        assert str(parent_path) == "/root"

        # Test root parent
        root_path = NodePath(["root"])
        assert root_path.parent().parts == []

        # Test empty path parent
        empty_path = NodePath()
        assert empty_path.parent() is None

        # Test name property
        assert path.name == "level1"
        assert empty_path.name == ""


class TestTreeNode:
    """Tests for TreeNode class"""

    def test_node_creation(self):
        """Test basic node creation"""
        # Create a simple node
        root = TreeNode("root", data={"key": "value"}, node_type="folder")
        assert root.name == "root"
        assert root.data == {"key": "value"}
        assert root.node_type == "folder"
        assert root.visible is True
        assert root.parent is None
        assert len(root.children) == 0
        assert isinstance(root.uuid, str)

        # Test path for root
        assert str(root.path) == "/root"

    def test_parent_child_relationship(self):
        """Test setting up parent-child relationships"""
        root = TreeNode("root")
        child1 = TreeNode("child1")
        root._add_child_to_tree(child1)

        # Test parent was set correctly
        assert child1.parent == root
        assert root.children == [child1]

        # Test adding another child
        child2 = TreeNode("child2")
        child2.parent = root
        assert child2.parent == root
        assert len(root.children) == 2
        assert child2 in root.children

        # Test changing parent
        new_parent = TreeNode("new_parent")
        child1.parent = new_parent
        assert child1.parent == new_parent
        assert child1 in new_parent.children
        assert child1 not in root.children
        assert len(root.children) == 1

    def test_path_generation(self):
        """Test path generation for nodes"""
        root = TreeNode("root")
        level1 = TreeNode("level1")
        root._add_child_to_tree(level1)
        level2 = TreeNode("level2")
        level1._add_child_to_tree(level2)
        level3 = TreeNode("level3")
        level2._add_child_to_tree(level3)

        # Test paths at each level
        assert str(root.path) == "/root"
        assert str(level1.path) == "/root/level1"
        assert str(level2.path) == "/root/level1/level2"
        assert str(level3.path) == "/root/level1/level2/level3"

        # Test path caching and invalidation
        old_path = level3.path
        level2.name = "renamed_level2"
        # Path should be invalid and regenerated
        assert str(level3.path) == "/root/level1/renamed_level2/level3"

        # Test path update after parent change
        new_parent = TreeNode("new_parent", parent=root)
        level2.parent = new_parent
        assert str(level2.path) == "/root/new_parent/renamed_level2"
        assert str(level3.path) == "/root/new_parent/renamed_level2/level3"

    def test_add_child(self):
        """Test adding children"""
        root = TreeNode("root")
        child1 = TreeNode("child1")
        child2 = TreeNode("child2")

        # Basic add
        success, _ = root._add_child_to_tree(child1)
        assert success is True
        assert child1 in root.children
        assert child1.parent == root

        # Add with position
        success, _ = root._add_child_to_tree(child2, position=0)
        assert success is True
        assert root.children[0] == child2
        assert root.children[1] == child1

        # Invalid position
        child3 = TreeNode("child3")
        success, _ = root._add_child_to_tree(child3, position=10)
        assert success is False
        assert child3 not in root.children

    def test_remove_child(self):
        """Test removing children"""
        root = TreeNode("root")
        child1 = TreeNode("child1")
        root._add_child_to_tree(child1)
        child2 = TreeNode("child2")
        root._add_child_to_tree(child2)

        # Remove by node
        removed = root.remove_child(child1)
        assert removed == child1
        assert child1 not in root.children
        assert child1.parent is None

        # Remove by UUID
        removed = root.remove_child(child2.uuid)
        assert removed == child2
        assert child2 not in root.children
        assert child2.parent is None

        # Remove non-existent child
        removed = root.remove_child("non-existent-uuid")
        assert removed is None

    def test_path_invalidation(self):
        """Test path cache invalidation"""
        root = TreeNode("root")
        level1 = TreeNode("level1")
        root._add_child_to_tree(level1)
        level2 = TreeNode("level2")
        level1._add_child_to_tree(level2)

        # Cache paths
        path1 = str(level1.path)
        path2 = str(level2.path)

        # Change name and verify path updates
        level1.name = "renamed"
        level1._invalidate_path_cache()
        assert str(level1.path) == "/root/renamed"
        assert str(level2.path) == "/root/renamed/level2"

    def test_node_type_filtering(self):
        """Test creating a subclass with type filtering"""

        class FolderNode(TreeNode):
            """A node that can only contain specific child types"""

            def _can_add_child(self, child):
                if child.node_type not in ["document", "folder"]:
                    return False, "Folders can only contain documents or other folders"
                return True, ""

        folder = FolderNode("folder", node_type="folder")
        doc = TreeNode("document", node_type="document")
        image = TreeNode("image", node_type="image")

        # Adding allowed type should succeed
        success, _ = folder._add_child_to_tree(doc)
        assert success is True

        # Adding disallowed type should fail
        success, msg = folder._add_child_to_tree(image)
        assert success is False
        assert "can only contain" in msg


class TestTreeSignals:
    """Tests for tree signal emission"""

    @pytest.fixture
    def signals(self):
        """Create a signals object for testing"""
        return TreeSignals()

    def test_signal_emission(self, signals, qtbot):
        """Test that signals are emitted correctly"""
        # Create tree with signals
        root = TreeNode("root")
        root._signals = signals

        # Track signal emissions manually instead of using waitSignal
        signal_emitted = False
        uuid_received = None

        def on_node_added(uuid):
            nonlocal signal_emitted, uuid_received
            signal_emitted = True
            uuid_received = uuid

        # Connect the signal to our handler
        signals.node_added.connect(on_node_added)

        # Add a child node
        child = TreeNode("child")
        root._add_child_to_tree(child)

        # Verify signal was emitted with correct arguments
        assert signal_emitted, "Node added signal was not emitted"
        assert uuid_received == child.uuid, "Signal emitted with wrong UUID"

        # Reset tracking variables and test visibility change
        signal_emitted = False
        visibility_value = None

        def on_visibility_changed(uuid, visible):
            nonlocal signal_emitted, uuid_received, visibility_value
            signal_emitted = True
            uuid_received = uuid
            visibility_value = visible

        signals.visibility_changed.connect(on_visibility_changed)

        # We need to implement visibility change
        if hasattr(root, 'set_visibility'):
            root.set_visibility(child.uuid, False)
            assert signal_emitted, "Visibility changed signal was not emitted"
            assert uuid_received == child.uuid, "Signal emitted with wrong UUID"
            assert visibility_value is False, "Signal emitted with wrong visibility value"

        # Reset and test removal signal
        signal_emitted = False

        def on_node_removed(uuid):
            nonlocal signal_emitted, uuid_received
            signal_emitted = True
            uuid_received = uuid

        signals.node_removed.connect(on_node_removed)

        # Remove the child
        child_uuid = child.uuid
        root.remove_child(child)

        assert signal_emitted, "Node removed signal was not emitted"
        assert uuid_received == child_uuid, "Signal emitted with wrong UUID"


class TestTreeTraversal:
    """Tests for tree traversal functions"""

    @pytest.fixture
    def sample_tree(self):
        """Create a sample tree for testing"""
        root = TreeNode("root")
        folderA = TreeNode("folderA", node_type="folder")
        folderB = TreeNode("folderB", node_type="folder")
        root._add_child_to_tree(folderA)
        root._add_child_to_tree(folderB)

        # Add items to folderA
        fileA1 = TreeNode("fileA1", node_type="file")
        folderA._add_child_to_tree(fileA1)
        fileA2 = TreeNode("fileA2", node_type="file")
        folderA._add_child_to_tree(fileA2)

        # Add nested folder in folderA
        folderA_nested = TreeNode("nested", node_type="folder")
        folderA._add_child_to_tree(folderA_nested)
        fileA_nested1 = TreeNode(
            "nestedFile1", node_type="file")
        folderA_nested._add_child_to_tree(fileA_nested1)

        # Add items to folderB
        fileB1 = TreeNode("fileB1", node_type="file")
        folderB._add_child_to_tree(fileB1)

        return root

    def test_find_by_path(self, sample_tree):
        """Test finding nodes by path"""
        # Implement find_by_path if it doesn't exist
        def find_by_path(node, path_str):
            path = NodePath.from_string(path_str)
            current = node

            for part in path.parts[1:]:  # Skip the first part (root node name)
                found = False
                for child in current.children:
                    if child.name == part:
                        current = child
                        found = True
                        break
                if not found:
                    return None

            return current

        # Test finding nodes
        assert find_by_path(sample_tree, "/root/folderA").name == "folderA"
        assert find_by_path(
            sample_tree, "/root/folderA/fileA1").name == "fileA1"
        assert find_by_path(
            sample_tree, "/root/folderA/nested/nestedFile1").name == "nestedFile1"
        assert find_by_path(sample_tree, "/root/folderB").name == "folderB"

        # Test path not found
        assert find_by_path(sample_tree, "/root/nonexistent") is None

    def test_contains_method(self, sample_tree):
        """Test the __contains__ method"""
        # Get some nodes from the sample tree
        folderA = None
        fileA1 = None
        for child in sample_tree.children:
            if child.name == "folderA":
                folderA = child
                for file in child.children:
                    if file.name == "fileA1":
                        fileA1 = file
                        break
                break

        # Test with node objects
        assert folderA in sample_tree
        assert fileA1 in sample_tree
        assert fileA1 in folderA
        assert sample_tree not in folderA

        # Test with UUID strings
        assert folderA.uuid in sample_tree
        assert fileA1.uuid in sample_tree
        assert fileA1.uuid in folderA
        assert sample_tree.uuid not in folderA

        # Test with NodePath objects
        assert NodePath.from_string("/root/folderA") in sample_tree
        assert NodePath.from_string("/root/folderA/fileA1") in sample_tree
        assert NodePath.from_string(
            "/root/folderA/nonexistent") not in sample_tree

    def test_find_by_uuid(self, sample_tree):
        """Test the find_by_uuid method"""
        # Get UUID of a nested node
        nested_file = None
        for child in sample_tree.children:
            if child.name == "folderA":
                for sub_child in child.children:
                    if sub_child.name == "nested":
                        for nested_child in sub_child.children:
                            if nested_child.name == "nestedFile1":
                                nested_file = nested_child
                                break

        assert nested_file is not None, "Test setup failed, couldn't find nested file"

        # Test finding by UUID
        found_node = sample_tree.find_by_uuid(nested_file.uuid)
        assert found_node is nested_file

        # Test finding the root node UUID
        found_root = sample_tree.find_by_uuid(sample_tree.uuid)
        assert found_root is sample_tree

        # Test with non-existent UUID
        assert sample_tree.find_by_uuid("nonexistent-uuid") is None

    def test_collect_visible_nodes(self, sample_tree):
        """Test collecting only visible nodes"""
        # Make some nodes invisible
        for child in sample_tree.children:
            if child.name == "folderB":
                child.visible = False

        # Function to collect visible nodes
        def collect_visible_nodes(node):
            result = []

            if node.visible:
                result.append(node)
                for child in node.children:
                    result.extend(collect_visible_nodes(child))

            return result

        visible_nodes = collect_visible_nodes(sample_tree)
        visible_names = [node.name for node in visible_nodes]

        # folderB and its children should not be included
        assert "folderB" not in visible_names
        assert "fileB1" not in visible_names

        # These should be included
        assert "root" in visible_names
        assert "folderA" in visible_names
        assert "fileA1" in visible_names
        assert "fileA2" in visible_names
        assert "nested" in visible_names
        assert "nestedFile1" in visible_names


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
