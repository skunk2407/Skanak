from economy.stats import load_stats, save_stats, get_user_stats

def migrate():
    stats = load_stats()
    for uid in list(stats.keys()):
        # l’appel complète chaque entrée avec tous les champs par défaut
        get_user_stats(stats, int(uid))
    save_stats(stats)
    print(f"[Migration] {len(stats)} utilisateurs mis à jour.")

# Si on exécute ce fichier directement, on migre
if __name__ == '__main__':
    migrate()