import pytest

from safevision.domain.structures.nary_tree import NaryTree


def keys(nodes) -> list[str]:
    return [node.key for node in nodes]


def tree_of(root: str, *edges: tuple[str, str]) -> NaryTree[str, int]:
    tree = NaryTree(root, 0)
    for parent, key in edges:
        tree.add_child(parent, key, 0)
    return tree


def test_a_tree_with_only_the_root():
    tree = NaryTree("a", 7)
    root = tree.find("a")
    assert (root.key, root.value, root.parent, root.children) == ("a", 7, None, [])
    assert tree.postorder() == [root]


def test_add_child_links_parent_and_child():
    tree = NaryTree("a", 0)
    tree.add_child("a", "b", 1)
    root, child = tree.find("a"), tree.find("b")
    assert child.parent is root
    assert root.children == [child]
    assert child.value == 1


def test_children_keep_the_insertion_order():
    tree = tree_of("a", ("a", "c"), ("a", "b"), ("a", "d"))
    assert keys(tree.find("a").children) == ["c", "b", "d"]


def test_postorder_of_a_wide_tree():
    tree = tree_of("a", ("a", "b"), ("a", "c"), ("a", "d"))
    assert keys(tree.postorder()) == ["b", "c", "d", "a"]


def test_postorder_of_a_chain():
    tree = tree_of("a", ("a", "b"), ("b", "c"), ("c", "d"))
    assert keys(tree.postorder()) == ["d", "c", "b", "a"]


def test_postorder_of_an_unbalanced_tree():
    r"""
         a
       / | \
      b  c  d
     / \    |
    e   f   g
            |
            h
    """
    tree = tree_of(
        "a",
        ("a", "b"),
        ("a", "c"),
        ("a", "d"),
        ("b", "e"),
        ("b", "f"),
        ("d", "g"),
        ("g", "h"),
    )
    assert keys(tree.postorder()) == ["e", "f", "b", "c", "h", "g", "d", "a"]


def test_every_node_comes_after_its_children():
    tree = tree_of("a", ("a", "b"), ("b", "c"), ("a", "d"), ("d", "e"), ("d", "f"))
    seen = set()
    for node in tree.postorder():
        assert all(child.key in seen for child in node.children)
        seen.add(node.key)


def test_add_child_rejects_an_unknown_parent():
    tree = NaryTree("a", 0)
    with pytest.raises(ValueError, match="unknown parent"):
        tree.add_child("x", "b", 1)
    assert tree.find("b") is None


@pytest.mark.parametrize("key", ["a", "b"])
def test_add_child_rejects_a_repeated_key(key):
    tree = NaryTree("a", 0)
    tree.add_child("a", "b", 1)
    first = tree.find("b")
    with pytest.raises(ValueError, match="duplicate key"):
        tree.add_child("b", key, 2)
    assert first.children == []
    assert tree.find("b") is first


def test_find_of_a_missing_key():
    assert NaryTree("a", 0).find("z") is None


def test_keys_may_be_tuples_of_different_kinds():
    tree = NaryTree(("root", 0), "raiz")
    tree.add_child(("root", 0), ("location", 1), "a")
    tree.add_child(("root", 0), ("camera", 1), "b")
    assert tree.find(("location", 1)).value == "a"
    assert tree.find(("camera", 1)).value == "b"
