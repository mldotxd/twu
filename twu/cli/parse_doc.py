# TWU parse 命令 - 解析原始文档（优化版）

import argparse
import platform
import shutil
import sys
from pathlib import Path


def get_optimal_ocr_options():
    """根据平台选择最佳 OCR 配置"""
    try:
        from docling.datamodel.pipeline_options import RapidOcrOptions, OcrMacOptions

        # macOS 优先使用原生 Vision
        if platform.system() == "Darwin":
            try:
                return OcrMacOptions(
                    lang=["zh-Hans", "zh-Hant", "en-US"],
                    recognition="accurate",
                )
            except Exception:
                pass

        # 默认使用 RapidOCR（轻量、中文效果好）
        return RapidOcrOptions(
            lang=["ch_sim", "en"],
            text_score=0.5,
        )
    except ImportError:
        return None


def parse_with_docling(file_path: Path, chunks_dir: Path, assets_dir: Path) -> tuple[bool, str]:
    """使用 Docling 解析 PDF/Word 文档（优化配置）"""
    try:
        from docling.document_converter import DocumentConverter, PdfFormatOption, WordFormatOption
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import (
            PdfPipelineOptions,
            TableStructureOptions,
            TableFormerMode,
        )
        from docling.datamodel.accelerator_options import AcceleratorOptions, AcceleratorDevice
        from docling_core.types.doc import PictureItem

        # 配置 PDF 管道（优化版）
        pdf_options = PdfPipelineOptions(
            # OCR 配置
            do_ocr=True,
            ocr_options=get_optimal_ocr_options(),

            # 表格提取（ACCURATE 模式，97.9% 准确率）
            do_table_structure=True,
            table_structure_options=TableStructureOptions(
                do_cell_matching=True,
                mode=TableFormerMode.ACCURATE,
            ),

            # 图片处理
            generate_picture_images=True,
            images_scale=2.0,

            # 硬件加速
            accelerator_options=AcceleratorOptions(
                num_threads=4,
                device=AcceleratorDevice.AUTO,
            ),

            # 超时设置
            document_timeout=120.0,
        )

        # 根据文件类型选择格式选项
        suffix = file_path.suffix.lower()
        if suffix == '.pdf':
            format_options = {
                InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)
            }
        else:
            # Word 文档使用默认配置
            format_options = {}

        converter = DocumentConverter(format_options=format_options)
        result = converter.convert(str(file_path))
        doc = result.document

        # 提取图片
        image_count = 0
        for element, _level in doc.iterate_items():
            if isinstance(element, PictureItem):
                try:
                    img = element.get_image(doc)
                    if img:
                        image_name = f"{file_path.stem}_{image_count}.png"
                        img.save(assets_dir / image_name, "PNG")
                        image_count += 1
                except Exception:
                    pass

        # 导出 Markdown
        markdown_content = doc.export_to_markdown()

        # 写入 chunks
        chunk_file = chunks_dir / f"{file_path.stem}.md"
        chunk_file.write_text(markdown_content, encoding='utf-8')

        return True, f"Docling 解析成功（ACCURATE 模式），提取 {image_count} 张图片"

    except ImportError as e:
        return False, f"Docling 未安装或缺少依赖: {e}"
    except Exception as e:
        return False, f"Docling 解析失败: {e}"


def parse_with_pypdf2(file_path: Path, chunks_dir: Path) -> tuple[bool, str]:
    """使用 PyPDF2 解析 PDF（兜底方案）"""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(file_path))
        text_parts = []

        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                text_parts.append(f"<!-- 第 {i+1} 页 -->\n\n{text}")

        content = "\n\n".join(text_parts)
        content = f"<!-- [解析质量待确认] 使用 PyPDF2 降级解析 -->\n\n{content}"

        chunk_file = chunks_dir / f"{file_path.stem}.md"
        chunk_file.write_text(content, encoding='utf-8')

        return True, f"PyPDF2 降级解析成功，共 {len(reader.pages)} 页"

    except ImportError:
        return False, "PyPDF2 未安装（pip install pypdf）"
    except Exception as e:
        return False, f"PyPDF2 解析失败: {e}"


def parse_with_python_docx(file_path: Path, chunks_dir: Path, assets_dir: Path) -> tuple[bool, str]:
    """使用 python-docx 解析 Word（兜底方案）"""
    try:
        from docx import Document
        from docx.opc.constants import RELATIONSHIP_TYPE as RT

        doc = Document(str(file_path))
        text_parts = []

        # 提取文本
        for para in doc.paragraphs:
            if para.text.strip():
                # 处理标题样式
                if para.style and para.style.name and para.style.name.startswith('Heading'):
                    level_str = para.style.name.replace('Heading ', '')
                    try:
                        level = int(level_str)
                        text_parts.append(f"{'#' * level} {para.text}")
                    except ValueError:
                        text_parts.append(para.text)
                else:
                    text_parts.append(para.text)

        # 提取图片
        image_count = 0
        for rel in doc.part.rels.values():
            if rel.reltype == RT.IMAGE:
                try:
                    image_data = rel.target_part.blob
                    ext = rel.target_part.content_type.split('/')[-1]
                    if ext == 'jpeg':
                        ext = 'jpg'
                    image_name = f"{file_path.stem}_{image_count}.{ext}"
                    (assets_dir / image_name).write_bytes(image_data)
                    text_parts.append(f"\n<!-- image: {image_name} -->\n")
                    image_count += 1
                except Exception:
                    pass

        content = "\n\n".join(text_parts)
        content = f"<!-- [解析质量待确认] 使用 python-docx 降级解析 -->\n\n{content}"

        chunk_file = chunks_dir / f"{file_path.stem}.md"
        chunk_file.write_text(content, encoding='utf-8')

        return True, f"python-docx 降级解析成功，提取 {image_count} 张图片"

    except ImportError:
        return False, "python-docx 未安装（pip install python-docx）"
    except Exception as e:
        return False, f"python-docx 解析失败: {e}"


def copy_markdown(file_path: Path, chunks_dir: Path) -> tuple[bool, str]:
    """复制 Markdown 文件"""
    try:
        content = file_path.read_text(encoding='utf-8')
        chunk_file = chunks_dir / file_path.name
        chunk_file.write_text(content, encoding='utf-8')
        return True, "Markdown 复制成功"
    except Exception as e:
        return False, f"Markdown 复制失败: {e}"


def copy_image(file_path: Path, assets_dir: Path) -> tuple[bool, str]:
    """复制图片文件"""
    try:
        shutil.copy2(file_path, assets_dir / file_path.name)
        return True, "图片复制成功"
    except Exception as e:
        return False, f"图片复制失败: {e}"


def main():
    """解析原始文档"""
    parser = argparse.ArgumentParser(
        description='解析原始文档（PDF/Word/Markdown/图片）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  twu parse 需求1              # 解析 需求1/raw/ 到 需求1/req/
  twu parse 需求1/raw          # 同上

处理流程:
  1. PDF/Word → Docling 解析（ACCURATE 模式，97.9% 表格准确率）
  2. Docling 失败 → PyPDF2/python-docx 降级
  3. Markdown → 直接复制
  4. 图片 → 复制到 assets/

OCR 引擎:
  - macOS: 原生 Vision（中英文）
  - 其他: RapidOCR（轻量、中文效果好）

输出:
  req/chunks/   文本分片（每个源文件一个 .md）
  req/assets/   图片资源

依赖安装:
  uv pip install docling        # 推荐（完整功能）
  uv pip install pypdf python-docx  # 兜底方案
'''
    )
    parser.add_argument('path', help='需求目录或 raw/ 目录路径')
    parser.add_argument('--force', '-f', action='store_true',
                        help='强制重新解析（清空已有 chunks/assets）')

    args = parser.parse_args()

    # 解析路径
    input_path = Path(args.path)

    # 判断是需求目录还是 raw/ 目录
    if input_path.name == 'raw':
        raw_dir = input_path
        req_dir = input_path.parent / 'req'
    else:
        raw_dir = input_path / 'raw'
        req_dir = input_path / 'req'

    # 检查 raw/ 目录
    if not raw_dir.exists():
        print(f"错误: raw/ 目录不存在: {raw_dir}")
        sys.exit(1)

    # 创建输出目录
    chunks_dir = req_dir / 'chunks'
    assets_dir = req_dir / 'assets'

    if args.force:
        if chunks_dir.exists():
            shutil.rmtree(chunks_dir)
        if assets_dir.exists():
            shutil.rmtree(assets_dir)

    chunks_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    # 扫描文件
    files = list(raw_dir.iterdir())
    if not files:
        print(f"警告: raw/ 目录为空: {raw_dir}")
        sys.exit(0)

    # 文件类型分类
    pdf_files = []
    word_files = []
    md_files = []
    image_files = []
    other_files = []

    for f in files:
        if f.is_file():
            suffix = f.suffix.lower()
            if suffix == '.pdf':
                pdf_files.append(f)
            elif suffix in ['.docx', '.doc']:
                word_files.append(f)
            elif suffix == '.md':
                md_files.append(f)
            elif suffix in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                image_files.append(f)
            else:
                other_files.append(f)

    print(f"扫描 raw/ 目录: {raw_dir}")
    print(f"  PDF: {len(pdf_files)} 个")
    print(f"  Word: {len(word_files)} 个")
    print(f"  Markdown: {len(md_files)} 个")
    print(f"  图片: {len(image_files)} 个")
    if other_files:
        print(f"  其他（跳过）: {len(other_files)} 个")
    print()

    # 检查 Docling 是否可用
    docling_available = False
    try:
        from docling.document_converter import DocumentConverter
        docling_available = True
        print("Docling: 已安装（ACCURATE 模式）")
    except ImportError:
        print("Docling: 未安装（将使用兜底方案）")
    print()

    results = []

    # 处理 PDF
    for f in pdf_files:
        print(f"处理 PDF: {f.name}")
        if docling_available:
            success, msg = parse_with_docling(f, chunks_dir, assets_dir)
            if not success:
                print(f"  Docling 失败: {msg}")
                print(f"  尝试 PyPDF2 降级...")
                success, msg = parse_with_pypdf2(f, chunks_dir)
        else:
            success, msg = parse_with_pypdf2(f, chunks_dir)
        print(f"  {msg}")
        results.append((f.name, success, msg))

    # 处理 Word
    for f in word_files:
        print(f"处理 Word: {f.name}")
        if docling_available:
            success, msg = parse_with_docling(f, chunks_dir, assets_dir)
            if not success:
                print(f"  Docling 失败: {msg}")
                print(f"  尝试 python-docx 降级...")
                success, msg = parse_with_python_docx(f, chunks_dir, assets_dir)
        else:
            success, msg = parse_with_python_docx(f, chunks_dir, assets_dir)
        print(f"  {msg}")
        results.append((f.name, success, msg))

    # 处理 Markdown
    for f in md_files:
        print(f"处理 Markdown: {f.name}")
        success, msg = copy_markdown(f, chunks_dir)
        print(f"  {msg}")
        results.append((f.name, success, msg))

    # 处理图片
    for f in image_files:
        print(f"处理图片: {f.name}")
        success, msg = copy_image(f, assets_dir)
        # 同时在 chunks 中创建占位符
        placeholder_file = chunks_dir / f"{f.stem}.md"
        placeholder_file.write_text(f"<!-- image: {f.name} -->\n", encoding='utf-8')
        print(f"  {msg}")
        results.append((f.name, success, msg))

    # 输出结果
    print()
    print("=" * 50)
    success_count = sum(1 for _, s, _ in results if s)
    fail_count = len(results) - success_count
    print(f"解析完成: 成功 {success_count} 个，失败 {fail_count} 个")
    print()
    print(f"输出目录:")
    print(f"  chunks: {chunks_dir}")
    print(f"  assets: {assets_dir}")
    print()
    print("下一步:")
    print(f"  Agent 阅读 chunks/ 和 assets/，生成 req/index.md")

    if fail_count > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
