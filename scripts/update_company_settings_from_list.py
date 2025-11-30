"""
提供されたリストに基づいて企業ごとの設定を更新するスクリプト
v3: ストーリーと投稿の両方を連携
v2: 投稿のみを連携（ストーリーはダウンロードもしない）
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict

# プロジェクトのルートパスをsys.pathに追加
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.utils import load_config, save_config


def parse_settings_list(settings_text: str) -> Dict[str, str]:
    """
    設定リストをパースして、instagram_id -> version (v2/v3)のマッピングを返す
    
    Args:
        settings_text: 設定リストのテキスト
        
    Returns:
        instagram_id -> version の辞書
    """
    mapping = {}
    lines = settings_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or line == '#N/A':
            continue
        
        # GLINK_v3 instagram_id または GLINK_v2 instagram_id の形式をパース
        match = re.match(r'GLINK_(v\d+)\s+(\S+)', line)
        if match:
            version = match.group(1)  # v2 or v3
            instagram_id = match.group(2)
            mapping[instagram_id] = version
    
    return mapping


def update_config_from_mapping(config_path: str, version_mapping: Dict[str, str]):
    """
    バージョンマッピングに基づいてconfig.jsonを更新
    
    Args:
        config_path: 設定ファイルのパス
        version_mapping: instagram_id -> version (v2/v3)のマッピング
    """
    config = load_config(config_path)
    
    if "targets" not in config or "companies" not in config["targets"]:
        print("[ERROR] targets.companiesが見つかりません")
        return False
    
    companies = config["targets"]["companies"]
    updated_count = 0
    not_found = []
    
    # 大文字小文字を区別しないマッピングを作成
    mapping_lower = {k.lower(): v for k, v in version_mapping.items()}
    
    for company in companies:
        if not isinstance(company, dict):
            continue
        
        instagram_id = company.get("instagram_id")
        if not instagram_id:
            continue
        
        # マッピングからバージョンを取得（大文字小文字を区別しない）
        version = version_mapping.get(instagram_id) or mapping_lower.get(instagram_id.lower())
        
        if not version:
            not_found.append(instagram_id)
            continue
        
        # バージョンに応じて設定を更新
        if version == "v3":
            # v3: ストーリーと投稿の両方を連携
            company["download_posts"] = True
            company["download_stories"] = True
            company["upload_posts"] = True
            company["upload_stories"] = True
            updated_count += 1
        elif version == "v2":
            # v2: 投稿のみを連携（ストーリーはダウンロードもしない）
            company["download_posts"] = True
            company["download_stories"] = False
            company["upload_posts"] = True
            company["upload_stories"] = False
            updated_count += 1
    
    # 設定を保存
    save_config(config, config_path)
    
    print(f"[OK] {updated_count}社の企業設定を更新しました")
    
    if not_found:
        print(f"[WARNING] {len(not_found)}社の企業が設定リストに見つかりませんでした:")
        for insta_id in not_found[:10]:  # 最初の10件のみ表示
            print(f"  - {insta_id}")
        if len(not_found) > 10:
            print(f"  ... 他 {len(not_found) - 10}件")
    
    return True


def main():
    """メイン関数"""
    # ユーザーが提供した設定リスト
    settings_list = """GLINK_v3 dahlia_seikotsu
GLINK_v2 kome_0604
GLINK_v3 fupao_y.higashiguchi
GLINK_v3 urutora.yokohama
GLINK_v2 1983_chigasaki
GLINK_v2 torikin_kinshicho
GLINK_v2 kushiraku_kinshicho
GLINK_v2 mekongyokohama
GLINK_v2 samosacenterminami
GLINK_v2 torisin.yokosuka.chuou
GLINK_v2 torisin.kurihama
GLINK_v2 torisin.kanazawabunko
GLINK_v2 torisin.sinsugita
GLINK_v2 hinotori_honten
GLINK_v2 chili_tori
GLINK_v2 teppannakata
GLINK_v2 0209babe
GLINK_v2 butakotamagawa
GLINK_v2 tamagawa3chome.sakaba
GLINK_v2 zekko_cho_nishifunabashi
GLINK_v2 funabori_zekko_cho
GLINK_v2 zekkocho.sonohachi
GLINK_v2 zekko_cho_mizue
GLINK_v2 monpin.mizue
GLINK_v2 ushiwakamaru0711
GLINK_v2 zekkoucho.naha
GLINK_v2 zekko_cho_motoyawata
GLINK_v2 zekko_cho_nishikasai
GLINK_v2 cantonese_en
GLINK_v2 hakatashouten.shibuya
GLINK_v2 yukinomura_shinbashi
GLINK_v2 chines_restauratrin
GLINK_v2 sumibiyaki.esuto7
GLINK_v2 toridensetsu.0925
GLINK_v2 china_garden_ziku
GLINK_v2 spicymonkeys_kamioooka
GLINK_v2 hashigoya_tunashima
GLINK_v2 umi_maguro_kamakura
GLINK_v2 kaburaya_takatsuki
GLINK_v2 kaburaya_ikebukuro2go
GLINK_v2 makibar.perca
GLINK_v2 manmaru_motosumi
GLINK_v2 kushikatsu_ichiro2
GLINK_v2 shintomi_uosen
GLINK_v2 bistro_syuhari
GLINK_v2 chigasaki_nine_two
GLINK_v2 yakinikucozou
GLINK_v3 sushidocorosou
GLINK_v2 lienlien_770
GLINK_v3 ks_bistro_costamesa
GLINK_v3 kanpai_santamonica
GLINK_v3 izakaya__micchan
GLINK_v3 hangryjoes_tokyo
GLINK_v3 warayun__west.yokochyo
GLINK_v3 ichirin_1129
GLINK_v2 horumonngunsou
GLINK_v3 warayun.noge
GLINK_v3 mangetsunogesaku
GLINK_v3 taisyuu_sakaba_otanisouten
GLINK_v3 yakinikuotani
GLINK_v3 yakitori_kabukiya
GLINK_v3 taishusakaba.aozora
GLINK_v3 maruhachi_8
GLINK_v3 affetto_miyazaki
GLINK_v3 amourmiyazaki
GLINK_v3 pm_201519
GLINK_v3 lecil_salon
GLINK_v3 hair.link
GLINK_v3 hair_make_street
GLINK_v3 vanille833
GLINK_v2 honihoni_koenji
GLINK_v3 sunaloha1997
GLINK_v3 bogl.beauty
GLINK_v3 lucidostyle_bogl
GLINK_v3 poteribakery_tokyo
GLINK_v3 supreme_ogaki
GLINK_v3 arsha_shaving.eyelash
GLINK_v3 classynail
GLINK_v3 enoshima_cafe_akua
GLINK_v3 nailsr.5
GLINK_v3 grand_line.www
GLINK_v3 tanno_seitaisitu
GLINK_v3 nikunosato_yokohama
GLINK_v3 nikuichiba_chigasaki
GLINK_v3 delamodeinsumi
GLINK_v3 lucidotanaka
GLINK_v3 arucuhr.maeda
GLINK_v3 art21_hearts
GLINK_v3 igagurishokudo
GLINK_v3 nail_la_mano_mie
GLINK_v3 ryogoku.cocoha.cafe
GLINK_v3 kakurega_naru_izakaya
GLINK_v3 kusabi_ibukey
GLINK_v3 kushikatsubilly
GLINK_v3 clalabymanisofhair
GLINK_v3 clala_kashihara
GLINK_v3 tsu_cestbien
GLINK_v3 amonde_0410
GLINK_v3 pixiebob_hairsalon
GLINK_v3 oshareclub26
GLINK_v3 shuhari.hachinohe
GLINK_v3 barber_beauty_salon_yamamoto
GLINK_v3 hfhsp2c
GLINK_v3 hfhsraffaello
GLINK_v3 hairmake_hanale
GLINK_v3 hairmakeao_c_al
GLINK_v3 hairmakeao_tiam
GLINK_v3 ao_perche
GLINK_v3 tgloss_kumamoto
GLINK_v3 neivshairfukkodai01
GLINK_v3 neivs_hair_teriha
GLINK_v3 bonita_saga_eyelash.brow
GLINK_v3 mitake2514
GLINK_v3 popular_este
GLINK_v3 popular_zenkunen
GLINK_v3 cuthouse_hiragishi
GLINK_v3 cabinetr
GLINK_v3 r.m.c_r_
GLINK_v3 aga.tha04
GLINK_v3 fiesta_grande.nail
GLINK_v3 beautysalonaanda
GLINK_v2 akihira.shibuya
GLINK_v2 aburiya_maruko
GLINK_v3 yakitoriazuma3553
GLINK_v2 zekko_cho_shitaya
GLINK_v3 salvia_mihata02
GLINK_v3 yamlapi_3b
GLINK_v3 lapishsakurada
GLINK_v3 dining_noa2022
GLINK_v3 crows.shinbashi
GLINK_v2 kaburaya_ikebukuro3go
GLINK_v3 shinka_tokyo_roppongi
GLINK_v3 fupao_sotetsu
GLINK_v3 arcana_amusement_bar
GLINK_v3 begokko_no_karubi
GLINK_v3 hashimoto_horumon
GLINK_v3 hide_niku
GLINK_v3 wadining_124
GLINK_v3 teppanyaki_124
GLINK_v3 harebare0819
GLINK_v2 sakaba_hiyoshimaru
GLINK_v3 fairytale_eyelash_
GLINK_v3 lucidostyle.bigen_eyelash
GLINK_v2 ginza_fukagawa_gen.an
GLINK_v2 robatayaki.shin
GLINK_v3 cerchio_0905
GLINK_v3 nikunosato_tennoutyou
GLINK_v3 rikumaru_tennoutyou
GLINK_v2 ichinokura2006
GLINK_v3 fupao_yokohama
GLINK_v3 fupao_turuyacho
GLINK_v3 fupao_noge_
GLINK_v3 seiryu_mangetu
GLINK_v3 aradati_kitchen
GLINK_v3 fupao_kichijoji
GLINK_v2 kusi_hiro94
GLINK_v3 kunitachi_zaemon
GLINK_v3 flap_isahaya_nagasaki_esthe
GLINK_v3 salon_de_prink
GLINK_v2 marumaru_shinbashihonten
GLINK_v3 accueillir_grace
GLINK_v3 accueillir_hair
GLINK_v3 eclat_hair_nagaoka
GLINK_v2 aizusoba_genbu
GLINK_v2 yakitori_fuuri_yokosuka
GLINK_v2 furi_isezaki
GLINK_v2 torigin_yonegahama
GLINK_v2 yatto_hanare
GLINK_v2 nishiazabu_fxloop
GLINK_v3 anartsoho_shun
GLINK_v2 gobugobu.0601
GLINK_v3 atelier_ojo
GLINK_v3 hair__mind
GLINK_v3 fupaokawasaki
GLINK_v3 nikunosato_odakyusagamihara
GLINK_v3 nikunosato_honatsugi
GLINK_v3 nikunosato_ebina
GLINK_v3 nikunosato_fujisawa
GLINK_v2 zekkocho_shitaya
GLINK_v3 lumi_915
GLINK_v3 fupao_tsurumi
GLINK_v3 phalaeno_white
GLINK_v2 hamburgrikishi
GLINK_v2 wagaya4_21_6
GLINK_v3 stastny.by.lumi
GLINK_v3 lumi_kamiooka
GLINK_v2 monpin.hirai
GLINK_v3 fupao_tsunashima
GLINK_v2 kaburaya_esaka
GLINK_v3 horumoncenter_otani_shouten
GLINK_v3 shisha_shee
GLINK_v3 sumibi_nao_yamato
GLINK_v3 don.napoli1110
GLINK_v3 chohakkai_no_daidokoro
GLINK_v3 pepek_0503
GLINK_v3 poteribakery_yokohama
GLINK_v3 bistro.campari
GLINK_v3 mangetu_yokohama
GLINK_v3 mangetsu_hanare
GLINK_v3 mangetu_ibuki
GLINK_v3 il_mare_azzurro_
GLINK_v3 fupao_takadanobaba
GLINK_v2 lumi.hairsalon
GLINK_v2 odenyahinata322"""
    
    print("=" * 60)
    print("企業ごとのストーリー・投稿連携設定を更新")
    print("=" * 60)
    print()
    
    # 設定リストをパース
    print("[INFO] 設定リストをパース中...")
    version_mapping = parse_settings_list(settings_list)
    print(f"[OK] {len(version_mapping)}社の設定を読み込みました")
    
    # バージョン別の統計
    v2_count = sum(1 for v in version_mapping.values() if v == "v2")
    v3_count = sum(1 for v in version_mapping.values() if v == "v3")
    print(f"  - v2（投稿のみ）: {v2_count}社")
    print(f"  - v3（ストーリー+投稿）: {v3_count}社")
    print()
    
    # config.jsonを更新
    print("[INFO] config.jsonを更新中...")
    config_path = "config/config.json"
    if update_config_from_mapping(config_path, version_mapping):
        print()
        print("=" * 60)
        print("[OK] 設定の更新が完了しました")
        print("=" * 60)
        print()
        print("設定内容:")
        print("  - v2: 投稿のみ連携（download_posts: true, download_stories: false, upload_posts: true, upload_stories: false）")
        print("  - v3: ストーリーと投稿の両方連携（すべて true）")
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("[ERROR] 設定の更新に失敗しました")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()

