import os
def get_directory_tree(path):
    tree = []
    for entry in os.listdir(path):
        full_path = os.path.join(path, entry)
        if os.path.isdir(full_path):
            tree.append({
                "name": full_path,
                "type": "folder",
                "children": get_directory_tree(full_path)
            })
        else:
            tree.append({
                "name": full_path,
                "type": "file"
            })
    return tree