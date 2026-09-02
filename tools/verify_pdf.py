#!/usr/bin/env python3
"""检查生成的 PDF：页数对不对，招聘系统能不能把里面的字抽出来。"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# **import 即把管道输出定到 UTF-8。** 这段说明 2026-08-23 从英文翻成中文之后，
# 被管道接走时在中文 Windows 上吐的是 GBK —— Git Bash / VS Code 终端一片乱码。
# `test_terminal_encoding` 当场抓到。这个脚本不在「被单独拷走」的名单里
# （只有 doctor / lint_skills / security_guards 是），所以可以 import。
import _cli  # noqa: E402,F401


class VerificationError(Exception):
    """这份 PDF 没通过检查。

    `missing_tool` 记的是「哪个命令没装」——**判据不能靠匹配错误文案**。
    `count_pages` 原来写的是 `if "was not found" not in str(exc)`，
    2026-08-23 把那句话翻成中文时当场把它打断了：pdfinfo 缺席的兜底再也不触发，
    `--pages` 在只有 pdftotext 的机器上永远报错 —— 而那正是 `count_pages`
    的注释记着的那个旧 bug（10 份刚编译好的简历全被误判）。
    换个字段，措辞怎么改都不影响判断。
    """

    def __init__(self, message, missing_tool=None):
        super().__init__(message)
        self.missing_tool = missing_tool


def run_tool(command):
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            # 必须显式指定 utf-8：text=True 默认按**本地**编码解码，而下面明确用
            # `pdftotext -enc UTF-8` 要的就是 UTF-8。在中文 Windows（cp936）上，
            # "张三" 会被解成三个完全不同的字，--contains 于是在一份文字确实存在的
            # PDF 上报「missing required text」。
            # errors="replace"：
            # 严格解码时无效字节会在 subprocess 的读取线程里抛 UnicodeDecodeError，
            # 那里没人接——run_tool 直接返回 None，下游 normalize_text(None) 再 AttributeError。
            encoding="utf-8",
            errors="replace",
        ).stdout
    except FileNotFoundError as exc:
        raise VerificationError(
            f"没装 {command[0]}（poppler 的一部分）—— 装上 poppler-utils 再跑",
            missing_tool=command[0],
        ) from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip() or (exc.stdout or "").strip()
        detail = detail or "命令失败了，没给原因"
        raise VerificationError(f"{command[0]} 读不了这个 PDF：{detail}") from exc


def parse_page_count(pdfinfo_output):
    match = re.search(r"^Pages:\s+(\d+)\s*$", pdfinfo_output, re.MULTILINE)
    if not match:
        raise VerificationError("pdfinfo 的输出里没有页数")
    return int(match.group(1))


def normalize_text(text):
    return " ".join(text.split())


def count_pages(pdf_path):
    """页数：优先 pdfinfo；**它没装时退回 pdftotext 的换页符计数**。

    poppler 的 Windows 发行版常只带 pdftotext 不带 pdfinfo——2026-08-12 实测：
    这台机器上 `--pages` 因此永远报错，10 份刚编译好的简历全被误判，肉眼再数
    才发现是工具缺席不是页数超标。而文本层校验本来就依赖 pdftotext，它在就够：
    pdftotext 在**每一页**末尾（含最后一页）输出一个 \\f，页数即 \\f 的个数。
    只在「命令不存在」时退回；pdfinfo 在但读不动文件仍然照常报错。
    """
    try:
        return parse_page_count(run_tool(["pdfinfo", str(pdf_path)]))
    except VerificationError as exc:
        # **看字段，不看文案。** 匹配错误文案的话，翻译一次就断（实测断过）。
        if exc.missing_tool != "pdfinfo":
            raise
        # **`-enc UTF-8` 这里也要带。** 数换页符本身不挑编码（它在哪种编码下
        # 都是同一个字节），所以漏了不会出错 —— 但 `run_tool` 是**写死按 UTF-8
        # 解码**的，不给 `-enc` 就等于让两端各自假设。同一个文件里另一处调用
        # 带着它（`verify_pdf` 里取正文那次），两处不一致的写法迟早被抄走一份
        # —— 而抄到取正文那条路上，中文就整批没了。
        pages = run_tool(
            ["pdftotext", "-enc", "UTF-8", str(pdf_path), "-"]).count("\f")
        if pages == 0:
            raise VerificationError(
                "没装 pdfinfo，而 pdftotext 没吐出换页符 —— 数不出页数"
            )
        return pages


#: 「字没嵌进去」在提取结果里长什么样。`�` 是解码失败的替换字符，
#: `□`（U+25A1）与 `�` 之外还有 `￼`（对象替换符，图片承载文字时出现）。
MOJIBAKE = ("�", "□", "￼")

#: 一份中文简历里汉字至少占提取文本的多少。低于它多半是**字体没嵌入**：
#: PDF 看着正常，招聘系统抽出来是一片方块或空白。
#:
#: 0.15 不是拍的，但也**不是从真实值往下取一点**。实测（2026-08-23，
#: `pdftotext -layout -enc UTF-8` 抽活动用户那两份简历）：**两份都是 55%**。
#: 而字体真没嵌进去时抽出来的是空白或标点，接近 0 —— 两端离得极远。
#:
#: 门槛压到 15% 是有意留 3.7 倍余量：**这一条误报的代价是拦住一次投递**，
#: 而它要抓的那个故障（0% 附近）离门槛远得很，压低不影响灵敏度。
#: 中英混排很重的简历（技术词、公司名、日期、数字连成片）才是这里真正的
#: 边界情况，15% 是给它们留的。
CJK_FLOOR = 0.15
_CJK = re.compile(r"[一-鿿]")


def cjk_ratio(text):
    """汉字占非空白字符的比例。空文本返回 0。"""
    body = re.sub(r"\s", "", text or "")
    return len(_CJK.findall(body)) / len(body) if body else 0.0


def verify_pdf(pdf_path, expected_pages=None, min_chars=1, required_text=(),
               expect_cjk=False):
    pdf_path = Path(pdf_path)
    if not pdf_path.is_file():
        raise VerificationError(f"找不到这个 PDF：{pdf_path}")

    if expected_pages is not None:
        actual_pages = count_pages(pdf_path)
        if actual_pages != expected_pages:
            raise VerificationError(
                f"页数应该是 {expected_pages}，实际 {actual_pages}"
            )

    extracted_text = normalize_text(
        run_tool(["pdftotext", "-layout", "-enc", "UTF-8", str(pdf_path), "-"])
    )
    if len(extracted_text) < min_chars:
        raise VerificationError(
            f"抽出来只有 {len(extracted_text)} 个字，至少要 {min_chars} 个"
        )

    for required in required_text:
        if normalize_text(required) not in extracted_text:
            raise VerificationError(f"文本层里找不到这段字：{required!r}")

    # **中文有没有变成方块，是这个工具本来最该查的一条，而它原来不查。**
    # `job-apply.md` Step 5e 把这一条列成了要人肉眼比对的清单项
    # （「不含 □ 与 �，CJK 字符数与简历实际内容量相称」）—— 而它纯机械。
    # 国内这条路很具体：Typst 字体没嵌进去 → PDF 看着正常 → 网申系统抽出来
    # 一片方块或空白 → 简历被判成没内容，而你永远不知道。
    # **乱码无条件查** —— 替换字符在哪种语言的简历里都是错的。
    hit = [c for c in MOJIBAKE if c in extracted_text]
    if hit:
        raise VerificationError(
            f"文本层里有 {len(hit)} 类乱码字符（{'、'.join(repr(c) for c in hit)}）"
            f"—— 多半是字体没嵌进 PDF，招聘系统会抽出一片方块")

    # **汉字占比要调用方声明，工具不猜简历是哪种语言。**
    # 默认关：外企/英文岗的简历本来就没有汉字，默认开会把它们全判成坏的
    # （加这一条时第一版就是默认开，当场顶红了一条用英文样例的既有测试）。
    # 中文简历走 `--cjk`，`job-apply.md` Step 5e 就是这么调的。
    if expect_cjk:
        ratio = cjk_ratio(extracted_text)
        if ratio < CJK_FLOOR:
            raise VerificationError(
                f"提取出来的字里只有 {ratio:.0%} 是汉字（至少要 {CJK_FLOOR:.0%}）"
                f"—— 一份中文简历不该是这样，先查字体有没有嵌进去")


def build_parser():
    # **这几句是印给用户看的，所以是中文。** 仓库规矩见 `AGENTS.md`
    # 「给用户看的措辞」——顺带那张表里明写着 `ATS` 这类未解释的英文码不许上屏，
    # 而这段说明原文就是 "Verify a PDF's page count and ATS-readable text layer."
    # 这个工具此前没有任何工作流调它，于是一直没人看见（2026-08-23 接进
    # `job-apply.md` Step 5e 之后就会被看见了）。
    parser = argparse.ArgumentParser(
        description="检查生成的 PDF：页数对不对，招聘系统能不能把里面的字抽出来。"
    )
    parser.add_argument("pdf", type=Path, help="要检查的 PDF 文件")
    parser.add_argument("--pages", type=int, help="页数必须正好是这个数")
    parser.add_argument(
        "--min-chars",
        type=int,
        default=1,
        help="抽出来的字（不含空白）至少要这么多个，默认 1",
    )
    parser.add_argument(
        "--contains",
        action="append",
        default=[],
        help="这段字必须能在抽出来的文本里搜到（手机号、邮箱），可以给多次",
    )
    parser.add_argument(
        "--cjk",
        action="store_true",
        help="这是中文简历：额外检查汉字占比，防字体没嵌进去（英文简历别加）",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        verify_pdf(args.pdf, args.pages, args.min_chars, args.contains,
                   expect_cjk=args.cjk)
    except VerificationError as exc:
        print(f"没通过：{args.pdf}：{exc}", file=sys.stderr)
        return 1
    print(f"检查通过：{args.pdf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
