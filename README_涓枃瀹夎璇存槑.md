# 知新·每日AI中文日报升级包

## 这次包含什么
- `index.html`：中文资讯网站，支持五大赛道分类、搜索、原文跳转、今日总结。
- `news_fetcher.py`：读取官方博客、科技媒体和 arXiv RSS，去重、分类，生成中文标题/摘要/价值判断。
- `.github/workflows/daily-news.yml`：每天北京时间约 08:20 自动运行，也可手动触发。
- `news.json`：网站读取的日报数据。

## 部署到现有 GitHub Pages 项目
你之前的网站仓库是 `wangqiuna714/ai-chinese-daily`，网址是 `https://wangqiuna714.github.io/ai-chinese-daily/`。

1. 在 GitHub 打开该仓库。
2. 将本升级包里的 `index.html`、`news_fetcher.py`、`news.json`、`requirements.txt` 上传到仓库根目录并替换同名文件。
3. 将 `.github/workflows/daily-news.yml` 上传到仓库的 `.github/workflows/` 文件夹；注意文件夹路径必须完全一致。
4. 配置中文摘要生成密钥：进入仓库 `Settings → Secrets and variables → Actions → New repository secret`。
   - Name 填：`GEMINI_API_KEY`
   - Secret 填你自己在 Google AI Studio 创建的 Gemini API key。
   - 不要把密钥写进网页、Python 文件或公开仓库。
5. 打开仓库 `Actions → Update AI Chinese Daily → Run workflow`，手动运行一次。
6. 等运行结束后刷新网站。后续工作流每天自动运行；GitHub Actions 的定时任务可能会有延迟。

## 重要说明
- 本项目使用公开 RSS/Atom 源作为线索入口，来源可用性和更新频率会变化；失败源会记录日志，其他源仍继续采集。
- Gemini API 用于中文编辑、摘要和每日总结。需要有效 API key，具体配额或费用以 Google AI Studio 账户政策为准。
- 如果没有配置 `GEMINI_API_KEY`，网站仍可打开，但自动中文摘要会显示失败提示；请先配置密钥再运行工作流。
- 自动摘要不是事实核查的替代品。重要信息应点击原文确认。
- 工作流每次会把更新后的 `news.json` 提交回仓库，GitHub Pages 随后发布。
