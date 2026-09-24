# AI生成
#!/usr/bin/env python3
"\n微头条内容 JS 生成器\n将中文内容转为 Unicode 转义 JS 表达式，用于 CDP /eval 输入到 ProseMirror 编辑器。\n\n用法:\n  python gen_weitoutiao_js.py --content \"微头条正文\" --output \"C:\\Users\\28470\\wt_content.js\"\n  python gen_weitoutiao_js.py --file content.txt --output \"C:\\Users\\28470\\wt_content.js\"\n"

import argparse
import sys


def to_unicode_escape(text):
    "将中文和非ASCII字符转为 \\uXXXX 转义，ASCII 字符保留原样。\n    同时转义换行符、回车、制表符、单引号和反斜杠，\n    防止 JS 单引号字符串语法错误。"
    result = []
    for ch in text:
        if ch == '\n':
            result.append('\\n')
        elif ch == '\r':
            result.append('\\r')
        elif ch == '\t':
            result.append('\\t')
        elif ch == "'":
            result.append("\\'")
        elif ch == '\\':
            result.append('\\\\')
        elif ord(ch) > 127:
            result.append(f'\\u{ord(ch):04x}')
        else:
            result.append(ch)
    return ''.join(result)


def generate_js(content):
    """生成完整的 JS 表达式"""
    escaped = to_unicode_escape(content)
    js = (
        "(function(){"
        "var e=document.querySelector('.ProseMirror');"
        "if(!e) return JSON.stringify({error:'no editor'});"
        "e.focus();"
        f"var text='{escaped}';"
        "document.execCommand('insertText',false,text);"
        "return JSON.stringify({len:e.textContent.length,preview:e.textContent.substring(0,100)});"
        "})()"
    )
    return js


def main():
    parser = argparse.ArgumentParser(description='微头条内容 JS 生成器')
    parser.add_argument('--content', type=str, help='微头条正文内容（直接传入）')
    parser.add_argument('--file', type=str, help='从文件读取正文内容')
    parser.add_argument('--output', type=str, required=True, help='输出 JS 文件路径')
    args = parser.parse_args()

    if args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
    elif args.content:
        content = args.content
    else:
        print("错误：必须提供 --content 或 --file 参数")
        sys.exit(1)

    js = generate_js(content)

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(js)

    char_count = len(content)
    chinese_count = sum(1 for ch in content if "一" <= ch <= "鿿")
    js_len = len(js)

    print(f"内容统计: {char_count} 字符, {chinese_count} 中文字")
    print(f"JS 长度: {js_len} 字符")
    print(f"输出文件: {args.output}")


if __name__ == '__main__':
    main()