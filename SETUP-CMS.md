# 臥龍会サイト：記事を誰でも入稿できるCMSの設定手順

「誰でも `studio.garyukai.jp/admin` から記事を書いて公開できる」状態にするための、一度だけの設定です。
所要 15〜20分。GitHubアカウント（無料・オーナーだけ）と、今のNetlifyサイトの管理権限が必要です。
編集者（お父様など）は **GitHubアカウント不要**。メール招待でログインできます。

---

## 仕組み（ざっくり）
- 記事の中身は `content/journal/○○.md` に保存されます。
- 保存すると Netlify が `build.py` を実行し、**今のデザイン・フォント・「琢」の点あり字形・SEO構造化データそのまま**で、記事ページ・一覧・英語版・sitemap を自動生成します。
- 編集者は `/admin` の入力画面（WordPress風）で日本語・英語の両方を入力 →「公開」。1〜2分で本番反映されます。

---

## 手順

### 1. GitHubに置く（オーナーが一度だけ）
1. GitHub で **空のリポジトリ**を作成（Private推奨）。名前は例：`garyukai-site`。READMEなどは追加しない。
2. このフォルダ（`garyu-site`）で、ターミナルから次を実行（`URL` は作ったリポジトリのもの）:
   ```bash
   cd "/Users/shunhigano/Downloads/書道研究 臥龍会/site/garyu-site"
   git remote add origin https://github.com/＜あなた＞/garyukai-site.git
   git push -u origin main
   ```
   ※ すでに初回コミットは作成済みです。上記でアップロードされます。

### 2. Netlify をこのリポジトリに接続
- 既存サイトにそのまま繋ぐ場合：Netlify管理画面 → 対象サイト → **Site configuration → Build & deploy → Continuous deployment → Link repository** → GitHubの `garyukai-site` を選択。
  - Build command / Publish は `netlify.toml` から自動設定されます（`pip install -r requirements.txt && python3 build.py` / 公開ディレクトリ `.`）。
- これ以降は **zipのドラッグは不要**。GitHubに変更が入ると自動でビルド＆公開されます。
- （ドメイン `studio.garyukai.jp` は今のまま維持されます）

### 3. ログイン基盤を有効化（Netlify Identity）
1. サイト → **Identity → Enable Identity**。
2. Identity → **Registration** を **Invite only**（招待制）に。
3. Identity → **Services → Git Gateway → Enable**。
   → これで、編集者はGitHubを持たなくても記事を保存できます。

### 4. 編集者を招待
- Identity → **Invite users** → お父様などのメールアドレスを入力して送信。
- 届いたメールのリンク → パスワード設定 → 自動で `/admin` に入れます。

### 5. 使い方（編集者向け）
1. `https://studio.garyukai.jp/admin` を開く →「Netlify Identity でログイン」。
2. 「読み物（記事）」→ **新規作成**。
3. 入力：
   - **スラッグ**：URLになる半角英数字（例 `spring-exhibition`）
   - 日本語／英語タイトル、カテゴリ、公開日
   - **アイキャッチ画像**（横長16:8推奨）をアップロード
   - 抜粋（日本語／英語）
   - 本文（日本語）／本文（English）※太字・見出し・箇条書き・リンク・画像が使えます
   - トップに出したい記事は「注目記事に表示」をON
4. 右上 **公開**（下書き確認したい場合は Editorial Workflow で「レビュー」も可）。
5. 1〜2分後、本番サイトに反映されます。

---

## 補足・注意
- **英語は人が入力**する設計です（自動翻訳ではありません）。英語本文が空だと英語ページの本文も空になります。
- 画像は `assets/uploads/` に保存されます。
- 「形式」は通常 `article`。質問→回答のインタビュー形式にしたい時だけ `qa`（見出しに「Q.」が付きます）。
- ローカルで生成物を確認したい場合：`python3 build.py` を実行（PyYAMLが必要：`pip install pyyaml`）。
- 既存の4記事もこのCMSに移行済みです。`/admin` から編集できます。
- 記事の削除・URL変更は慎重に（SEOに影響）。困ったら日賀野（オーナー）まで。
