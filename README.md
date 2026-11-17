# 每日收盘复盘

网站：https://wanan99999.github.io/market-review/

- 在网站右上角「上传复盘」上传当天的 Word（.docx），GitHub Actions 会自动解析并发布，约 1–2 分钟。
- 也可以直接把 .docx 放进 `inbox/` 文件夹提交。
- 解析结果在 `data/YYYY-MM-DD.json`，原文件归档到 `docx/`；解析失败的文件会移到 `inbox/failed/`。
- 生成脚本：`python scripts/build.py`（只用标准库）。
