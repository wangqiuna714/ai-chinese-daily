《知新 · AI 每日中文简报》互联网版（GitHub Pages 免费部署）

本版不需要电脑安装 Python，也不用启动黑色窗口。上线后可以在手机、平板、其他电脑打开。

发布操作：
1. 登录 https://github.com/ 并创建 Public（公开）仓库，仓库名称例如 ai-chinese-daily，勾选添加 README。
2. 打开新仓库 → Add file → Upload files，把本压缩包解压后的 index.html、news.json、update_news.py、news_fetcher.py 上传到仓库根目录，然后提交（Commit changes）。
3. 注意 .github/workflows/daily-news.yml 是隐藏文件夹内文件。网页上传不方便上传隐藏目录时：仓库 Add file → Create new file，文件名直接输入 .github/workflows/daily-news.yml，再将解压后该文件的全部内容粘贴进去，提交。
4. 仓库 → Settings → Pages → Build and deployment → Source 选 Deploy from a branch → Branch 选 main 和 /(root) → Save。
5. 稍等 GitHub 完成部署；网页版地址通常为 https://你的GitHub用户名.github.io/ai-chinese-daily/ （实际以 Pages 页面显示为准）。
6. 仓库 → Actions → 左侧“每日更新 AI 中文资讯” → Run workflow → Run workflow。等待运行成功，刷新线上网页，即可看见最新抓取的资讯。

之后：GitHub Actions 每天北京时间 08:20 尝试抓取相关新闻，自动更新 news.json 并触发网站更新。免费服务的计划任务可能延迟，且若新闻 RSS 网络访问失败则可能保持旧数据；留意网页的日期和新闻原文时间。网页“刷新资讯”只是读取最新已发布数据，不能实时触发 GitHub 上的抓取任务。

说明：
- 所有界面、知识教学、每日总结均为简体中文；新闻优先采集中文来源，外文原文页面通过“中文阅读”按钮交给浏览器翻译服务，翻译是否成功由第三方网站决定。
- 新闻标题为 RSS 源实时取得，并附原文链接。每日总结依据标题生成，供快速浏览，不等于全文研读。
- 搜索/收藏在各自浏览器本地完成，不跨设备同步。
- 完整网站代码托管在你自己的 GitHub 公开仓库，别人也可查看网页源码。不要放入私人资料。
