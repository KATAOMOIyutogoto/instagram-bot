"""
credentials.json の設定を確認・修正するスクリプト
デスクトップアプリ版に必要な設定を追加します
"""

import json
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def setup_credentials():
    """credentials.json の設定を確認・修正"""
    credentials_path = Path("config/credentials.json")

    if not credentials_path.exists():
        print(f"[ERROR] {credentials_path} が見つかりません")
        print("\n以下の手順で credentials.json を作成してください：")
        print("1. Google Cloud Console にアクセス")
        print("2. 「APIとサービス」→「認証情報」に移動")
        print("3. 「認証情報を作成」→「OAuth クライアント ID」を選択")
        print("4. アプリケーションの種類: 「デスクトップアプリ」を選択")
        print("5. JSONファイルをダウンロードして config/credentials.json として保存")
        return False

    try:
        # 現在の設定を読み込み
        with open(credentials_path, encoding="utf-8") as f:
            creds_data = json.load(f)

        print(f"[OK] {credentials_path} を読み込みました")
        print("\n現在の設定を確認中...")

        # installed キーの確認
        if "installed" not in creds_data:
            if "web" in creds_data:
                print("[WARNING] 'web' 形式が検出されました。'installed' 形式に変換します...")
                creds_data["installed"] = creds_data.pop("web")
            else:
                print("[ERROR] 'installed' または 'web' キーが見つかりません")
                return False

        installed_config = creds_data["installed"]

        # 必須フィールドの確認
        required_fields = ["client_id", "project_id", "auth_uri", "token_uri", "client_secret"]
        missing_fields = [field for field in required_fields if field not in installed_config]

        if missing_fields:
            print(f"[ERROR] 必須フィールドが不足しています: {', '.join(missing_fields)}")
            return False

        print("[OK] 必須フィールドはすべて揃っています")

        # redirect_uris の確認・追加
        if "redirect_uris" not in installed_config:
            installed_config["redirect_uris"] = []

        redirect_uris = installed_config["redirect_uris"]
        required_redirect_uris = [
            "http://localhost",
            "http://localhost:8080",
            "urn:ietf:wg:oauth:2.0:oob",  # コンソールベース認証用
        ]

        updated = False
        for uri in required_redirect_uris:
            if uri not in redirect_uris:
                redirect_uris.append(uri)
                updated = True
                print(f"[OK] リダイレクトURIを追加: {uri}")

        if not updated:
            print("[OK] リダイレクトURIは既に設定されています")

        # auth_provider_x509_cert_url の確認（オプション）
        if "auth_provider_x509_cert_url" not in installed_config:
            installed_config["auth_provider_x509_cert_url"] = (
                "https://www.googleapis.com/oauth2/v1/certs"
            )
            updated = True
            print("[OK] auth_provider_x509_cert_url を追加しました")

        # 設定を保存
        if updated:
            # バックアップを作成
            backup_path = credentials_path.with_suffix(".json.backup")
            if not backup_path.exists():
                with open(backup_path, "w", encoding="utf-8") as f:
                    json.dump(creds_data, f, indent=2, ensure_ascii=False)
                print(f"[OK] バックアップを作成: {backup_path}")

            # 更新された設定を保存
            with open(credentials_path, "w", encoding="utf-8") as f:
                json.dump(creds_data, f, indent=2, ensure_ascii=False)
            print(f"\n[OK] {credentials_path} を更新しました")
        else:
            print("\n[OK] 設定は既に正しく構成されています")

        # 最終確認
        print("\n" + "=" * 60)
        print("設定の確認結果")
        print("=" * 60)
        print(f"クライアントID: {installed_config['client_id']}")
        print(f"プロジェクトID: {installed_config['project_id']}")
        print("リダイレクトURI:")
        for uri in redirect_uris:
            print(f"  - {uri}")
        print("=" * 60)

        print("\n[OK] credentials.json の設定が完了しました！")
        print("\n次のステップ:")
        print("1. Google Cloud Console で以下のリダイレクトURIが設定されているか確認:")
        for uri in redirect_uris:
            print(f"   - {uri}")
        print("2. python scripts/get_gbp_ids.py を実行して認証を開始")

        return True

    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON解析エラー: {e}")
        print("credentials.json の形式が正しくない可能性があります")
        return False
    except Exception as e:
        print(f"[ERROR] エラー: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("credentials.json 設定ツール")
    print("=" * 60)
    print()

    success = setup_credentials()

    if not success:
        sys.exit(1)
