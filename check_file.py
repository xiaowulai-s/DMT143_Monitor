import core.serial_client as sc
import inspect

src = inspect.getsourcefile(sc.DMT143Client)
print("源文件:", src)

# 检查文件内容
with open(src, 'r', encoding='utf-8') as f:
    content = f.read()
    if '_dewpoint_change_limit' in content:
        print("文件包含阈值变量")
    else:
        print("文件不包含阈值变量")
