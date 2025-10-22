import os
import json
from typing import Dict

BADGES = {
  'first_work': {
    'name': '🔨 First Work',
    'description': 'You did your first `!work`',
    'url': 'https://cdn.discordapp.com/attachments/1381301971570397184/1381319243509006457/first_work.png?ex=6847154b&is=6845c3cb&hm=aa238fc8d2c222135fccd65199b48865af34bec9774edea6425b3f1b9244addf&'
  },
  'streak_7': {
    'name': '🔥 7-Day Streak',
    'description': 'Claimed daily reward 7 days in a row',
    'url': 'https://cdn.discordapp.com/attachments/1381301971570397184/1381319276555927803/streak_7.png?ex=68471553&is=6845c3d3&hm=99eca72d889ccd5396b5d7aabf92516a31747bc285e5ae63f32578edb3f16315&'
  },
  'shop_veteran': {
    'name': '🛒 Shop Veteran',
    'description': 'Made 10 purchases in the shop',
    'url': 'https://cdn.discordapp.com/attachments/1381301971570397184/1381319285225558108/shop_veteran.png?ex=68471555&is=6845c3d5&hm=daf6db07a2330b700c10bcdf47219a9d11d9f75d9cb00303b9fe80209fd95de5&'
  },
  'certified': {
    'name': '🧀 Certified Enjoyer',
    'description': 'Unlocked the special role via `!cheese`',
    'url': 'https://cdn.discordapp.com/attachments/1381301971570397184/1381319281030991892/certified.png?ex=68471554&is=6845c3d4&hm=8fa76695a6c7e68c4028b8944bb3420c5cc8dc6b4c68576074474493cbdeb67d&'
  },
  'streak_30': {
    'name': '🏅 30-Day Streak',
    'description': 'Claimed daily reward 30 days in a row',
    'url': 'https://cdn.discordapp.com/attachments/1381301971570397184/1381319290896122016/streak_30.png?ex=68471556&is=6845c3d6&hm=8c6ecb41e36cf624f54848f8ee8beecc03f8c90dabf554e9e96acb4ca920fee6&'
    },
    'wealth_1m': {
      'name': '💰 Millionaire',
      'description': 'Accrued 1 000 000 🧀 total balance',
      'url': 'https://cdn.discordapp.com/attachments/1381301971570397184/1381319299662217347/wealth_1m.png?ex=68471558&is=6845c3d8&hm=2c97a2d7c13d551586c9199ae7a74796c637b5b9f27d7638a482f30f2c40782b&'
    },
    'master_thief': {
      'name': '🗡️ Master Thief',
      'description': 'Successfully stole from 50 different users',
      'url': 'https://cdn.discordapp.com/attachments/1381301971570397184/1381319305303556188/master_chief.png?ex=6847155a&is=6845c3da&hm=4778009df6356caf7690585b4604ec729448686a169a9491f44d88a965b6986c&'
    },
    'shop_legend': {
      'name': '🎖️ Shop Legend',
      'description': 'Made 100 purchases in the shop',
      'url': 'https://cdn.discordapp.com/attachments/1381301971570397184/1381319311414530108/shop_legend.png?ex=6847155b&is=6845c3db&hm=de20b11a35ec2a502dee5d2564d7d7d774856dd4e5e273cd7a81fa92e78ce22b&'
    },
    'gift_giver': {
      'name': '🎁 Generous Giver',
      'description': 'Shared at least 50 000 🧀 in total',
      'url': 'https://cdn.discordapp.com/attachments/1381301971570397184/1381319339495526550/gift_giver.png?ex=68471562&is=6845c3e2&hm=f28b6de2e934cc80f349cdfa5a18f0b560be179640a4581c3930bc4674a92a29&'
    },
    'speed_runner': {
      'name': '⚡ Speed Runner',
      'description': 'Ran !work and !daily back-to-back in under 1 min 10 times',
      'url': 'https://cdn.discordapp.com/attachments/1381301971570397184/1381319331144798338/speed_runner.png?ex=68471560&is=6845c3e0&hm=ffac8b5ab0f0a9b75db005bc1507a2333c373b850a4b967e2007981789e47aca&'
    },
    'underdog': {
        'name': '🐭 Underdog',
        'description': 'Stole more cheese than you ever earned (net steal > earned)',
        'url': 'https://cdn.discordapp.com/attachments/1381301971570397184/1381319325092151437/underdog.png?ex=6847155e&is=6845c3de&hm=9365919488232f9b502552e4a6b9bc61897350542af48a20104c9e09623f87d8&'
    },
    'hoarder': {
        'name': '🏰 Hoarder',
        'description': 'Reached 150 000 🧀 without ever spending in shop',
        'url': 'https://cdn.discordapp.com/attachments/1381301971570397184/1381319320943988787/hoarder.png?ex=6847155d&is=6845c3dd&hm=6820bbbe566290880d2676ce69188b8d479e94f94ac5957d5be9c9cd9e4ead13&'
    },
    'raid_boss': {
        'name': '👑 Raid Boss',
        'description': 'Been stolen from 10 times in a row',
        'url': 'https://cdn.discordapp.com/attachments/1381301971570397184/1381319335498223687/raid_boss.png?ex=68471561&is=6845c3e1&hm=13b0342cc926c750d8c340f896068a9ab5c9d0b0c9ed66fa8b1689e5055058da&'
    }
}

# === utilitaires badge ===
USER_STATS = os.path.join(os.path.dirname(__file__), 'user_stats.json')

def load_stats() -> Dict:
    if not os.path.exists(USER_STATS):
        return {}
    with open(USER_STATS, 'r') as f:
        return json.load(f)

def save_stats(stats: Dict):
    with open(USER_STATS, 'w') as f:
        json.dump(stats, f, indent=4)

def award_badge(user_id: int, badge_key: str) -> bool:
    """
    Ajoute badge_key à l'utilisateur si absent, retourne True si nouvel ajout.
    """
    stats = load_stats()
    uid = str(user_id)
    entry = stats.setdefault(uid, {'cheese': 0, 'badges': []})
    entry.setdefault('badges', [])
    if badge_key not in entry['badges']:
        entry['badges'].append(badge_key)
        save_stats(stats)
        return True
    return False