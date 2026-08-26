# 决策器（第一期：网页记账）

一套能在**手机浏览器和电脑浏览器**打开的记账网页。同一邮箱登录后，读写的是云端同一份数据。购买决策（AI）第二期再加。

本地开发默认用 SQLite（`data/app.db`）。部署到网上后，把 `DATABASE_URL` 指到 PostgreSQL，手机在 4G 下也能记。

## 依赖

```text
pip install -r requirements.txt
```

需要 Python 3.10 或更高版本。

## 本机运行

在项目文件夹里执行：

```powershell
cd "c:\Users\15718\Desktop\决策器"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

浏览器打开：http://127.0.0.1:5000

同一 WiFi 下用手机试：电脑和手机连同一个无线网，手机浏览器输入 `http://电脑局域网IP:5000`（IP 可在 Windows 用 `ipconfig` 看无线网卡的 IPv4）。这只适合家里试用。出门同步必须部署到公网。

## 使用

1. 注册一个邮箱账号（密码至少 6 位）
2. 在「我的」里设置月预算
3. 首页记一笔，明细里可按月查看和删除

## 部署（真双端同步）

以 [Render](https://render.com/) 为例：

1. 把项目放到 GitHub
2. Render 新建 Web Service，构建命令 `pip install -r requirements.txt`，启动命令会读 `Procfile`
3. 再新建一个 PostgreSQL，把生成的 `DATABASE_URL` 填进 Web Service 的环境变量
4. 再设置 `SECRET_KEY` 为一串随机字符（不要用开发默认值）
5. 部署完成后，用 `https://你的地址` 在手机和电脑分别登录同一个邮箱

Render 免费实例一段时间没人访问会休眠，第一次打开可能要等十几秒。

## 新手注意事项

- 金额只填数字，不要写「35元」。
- 必须先部署到公网，手机离开家里 WiFi 才能继续记账。只在电脑上 `python app.py` 不是云同步。
- 不要把 `.env`、`data/app.db` 发到公开仓库。
- 第二期才会加「买不买」对话；现在先把每天花了多少记清楚。
