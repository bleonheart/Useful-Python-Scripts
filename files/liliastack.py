import os

def stack_lua_files():
    source_dir = r'C:\Users\David\Desktop\lilia'
    output_file = os.path.join(source_dir, 'output.lua')

    if not os.path.isdir(source_dir):
        print(f"Error: '{source_dir}' is not a valid directory.")
        return

    lua_files = []
    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.endswith('.lua'):
                full_path = os.path.join(root, file)
                lua_files.append(full_path)

    lua_files.sort()

    with open(output_file, 'w', encoding='utf-8') as outfile:
        for file in lua_files:
            with open(file, 'r', encoding='utf-8-sig') as infile:
                content = infile.read()
                outfile.write(f"-- {file}\n")
                outfile.write(content)
                outfile.write("\n\n")

if __name__ == '__main__':
    stack_lua_files()