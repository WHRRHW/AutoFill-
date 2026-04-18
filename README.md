# AutoFill - 智能文档结构化填报助手

一个面向业务人员的 Windows 桌面工具：上传源文档（Word/PDF）和 Word 模板后，自动抽取结构化信息并填充到模板占位符中，输出可直接交付的 DOCX 文档，同时尽量保持模板原有排版与表格样式不变。

## 产品目标

- 降低人工“阅读材料 + 填模板”的重复劳动成本
- 提高字段提取一致性，减少漏填和错填
- 通过 `docxtpl` 占位符渲染实现格式稳定输出

## 核心能力

- 源文档输入：支持 `.docx` 与文本型 `.pdf`
- 模板驱动抽取：自动扫描模板中的 `{{变量名}}` 作为抽取字段
- LLM 结构化输出：调用豆包模型 `doubao-seed-2-0-mini-260215`，要求返回 JSON
- 字段对齐校验：输出 matched / missing / extra / 空值提示
- 人工修正兜底：支持在 UI 中编辑 JSON 后再渲染
- 无损渲染导出：生成新 DOCX 文件（不覆盖原模板）

## 技术栈

- UI：`CustomTkinter`
- 文档解析：`python-docx`、`pdfplumber`
- 结构化抽取：`openai` SDK（豆包兼容接口）
- 模板渲染：`docxtpl`
- 数据校验：`pydantic`

## 项目结构

```text
app/
  application/            # 用例编排、工作流服务
  domain/                 # 领域模型、校验、错误定义
  infrastructure/
    config/               # 配置与凭据读取（环境变量）
    document/             # DOCX/PDF 读取
    llm/                  # Prompt 构建、模型客户端
    template/             # 模板变量扫描、渲染
    storage/              # 输出命名、模板库等
  ui/                     # CustomTkinter 界面
  main.py                 # 程序入口
scripts/                  # 校验与打包脚本
tests/                    # 回归测试
```

## 环境准备

建议 Python 3.10+（Windows）。

1. 创建并激活虚拟环境（可选）
2. 安装依赖：

```bash
pip install -r docs/requirements.txt
```

开发/测试额外依赖：

```bash
pip install -r docs/requirements-dev.txt
```

## 安装包使用方式（推荐业务用户）

仓库已提供 Windows 安装包：

- `dist/AutoFill 1.0.1.zip`

使用步骤：

1. 从仓库下载 `dist/AutoFill 1.0.1.zip`
2. 解压到任意目录（建议非系统盘）
3. 进入解压后的 `AutoFill` 目录
4. 双击可执行文件启动程序
5. 按界面指引选择源文档与模板后生成结果文档

说明：

- 安装包模式通常不需要本机额外安装 Python
- 模型服务仍依赖环境变量（见下方“必要环境变量”）

## 必要环境变量

运行前请在系统或终端中预置以下变量（UI 不提供手动配置入口）：

- `AUTO_FILL_API_KEY`：模型服务 API Key
- `AUTO_FILL_API_BASE_URL`：模型服务 Base URL

可选高级参数：

- `AUTO_FILL_MAX_SOURCE_CHARS`：送入模型的最大源文本长度
- `AUTO_FILL_MAX_OUTPUT_TOKENS`：模型最大输出 token
- `AUTO_FILL_REFILL_EMPTY`：是否对空值字段执行二次补抽（`true/false`）

PowerShell 示例：

```powershell
$env:AUTO_FILL_API_KEY="your_api_key"
$env:AUTO_FILL_API_BASE_URL="https://your-compatible-endpoint/v1"
```

## 启动方式

在项目根目录执行：

```bash
python -m app.main
```

## 使用流程

1. 选择源文档 A（Word/PDF）
2. 选择模板文档 B（含 `{{变量名}}` 占位符）
3. 点击“开始提取”，等待 JSON 结果与匹配报告
4. 按需在右侧编辑 JSON
5. 点击“生成文档”，输出到配置目录

## 输入输出约束

- A 文档：`.docx` / 文本型 `.pdf`
- B 模板：`.docx`，且必须预置 `{{变量名}}`
- 输出：新 `.docx` 文件（默认带时间戳命名）

## 当前边界与已知限制

- 不支持 OCR：扫描件/图片型 PDF 可能无法正确抽取
- 不包含多人协作、云端账号与审批流
- 当前默认输出 DOCX，不直接导出 PDF

## 质量与验收关注点

- 模板格式稳定性（表格、边框、字体、段落）
- 抽取字段完整性（missing/empty 字段可定位）
- 错误可恢复性（重试、提示、手工修正）

## 常用脚本

- `scripts/verify_render.py`：本地渲染链路验证
- `scripts/verify_llm_offline.py`：离线/替代条件下抽取链路验证
- `scripts/verify_workflow_offline.py`：工作流联调验证

## 版本规划（简要）

- 迭代 0（Demo）：端到端最小闭环（已完成）
- 迭代 1（Beta）：PDF 支持、映射校验、重试机制（已完成主体）
- 迭代 2（v1.0）：完整性报告、性能优化与稳定化（进行中）
- 迭代 3（v1.5+）：批处理、可配置能力与增强工具（规划中）

## 仓库地址

- GitHub: [WHRRHW/AutoFill-](https://github.com/WHRRHW/AutoFill-.git)
