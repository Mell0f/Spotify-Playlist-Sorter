import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv

load_dotenv()

# --- Bloco de Funções com Responsabilidade Única ---

def get_spotify_client():
    """Autentica o usuário e retorna um cliente Spotipy conectado."""
    print("Conectando ao Spotify...")
    scope = "playlist-modify-public playlist-modify-private playlist-read-private"
    auth_manager = SpotifyOAuth(scope=scope)
    sp = spotipy.Spotify(auth_manager=auth_manager)
    print("Conectado com sucesso!")
    return sp

def get_all_playlist_tracks_with_details(sp, playlist_id):
    """
    Busca todas as músicas de uma playlist e extrai uma lista detalhada
    de dicionários, um para cada música, contendo apenas o que precisamos para ordenar.
    """
    print(f"Buscando músicas...")
    playlist_items = []
    results = sp.playlist_items(playlist_id)
    playlist_items.extend(results['items'])
    
    while results['next']:
        results = sp.next(results)
        playlist_items.extend(results['items'])

    tracks_details = []
    for item in playlist_items:
        track = item.get('track')
        if not track or not track.get('uri'):
            continue  # Pula faixas indisponíveis ou locais

        # Coleta todas as informações em uma "ficha completa"
        details = {
            'uri': track['uri'],
            'name': track['name'].lower(),
            'artist': track['artists'][0]['name'].lower(),
            'album': track['album']['name'].lower(),
            'release_date': track['album']['release_date'],
            'popularity': track['popularity'],
            'added_at': item['added_at']
        }
        tracks_details.append(details)
    
    print(f"{len(tracks_details)} músicas encontradas e prontas para ordenar.")
    return tracks_details

def display_menu_and_get_choices():
    """
    Mostra o menu de opções para o usuário e captura suas escolhas de
    ordenação e direção.
    """
    # Mapeia o número da opção para a chave de dados e um nome
    sort_options = {
        '1': ('artist', 'Artista'),
        '2': ('album', 'Álbum'),
        '3': ('release_date', 'Data de Lançamento'),
        '4': ('added_at', 'Data de Adição'),
        '5': ('popularity', 'Popularidade'),
        '6': ('name', 'Nome da Música (Alfabética)'),
    }

    print("\n--- Escolha os Critérios de Ordenação ---")
    for key, (data_key, name) in sort_options.items():
        print(f"  {key} - {name}")

    chosen_keys = []
    while len(chosen_keys) < len(sort_options):
        priority = len(chosen_keys) + 1
        choice = input(f"Escolha o {priority}º critério (ou pressione Enter para finalizar): ")
        if not choice:
            break
        if choice in sort_options and sort_options[choice][0] not in chosen_keys:
            chosen_keys.append(sort_options[choice][0])
        else:
            print("Opção inválida ou já escolhida. Tente novamente.")
    
    if not chosen_keys:
        return None, None # Usuário não escolheu nada

    print("\n--- Escolha a Direção da Ordenação ---")
    print("  1 - Crescente (A-Z, Mais antiga, Menos popular)")
    print("  2 - Decrescente (Z-A, Mais nova, Mais popular)")
    
    while True:
        direction_choice = input("Escolha a direção (1 ou 2): ")
        if direction_choice == '1':
            reverse_sort = False
            break
        elif direction_choice == '2':
            reverse_sort = True
            break
        else:
            print("Opção inválida. Tente novamente.")
            
    return chosen_keys, reverse_sort

def reorder_playlist_in_spotify(sp, playlist_id, sorted_track_uris):
    """Substitui as faixas da playlist pela nova lista ordenada."""
    if not sorted_track_uris:
        print("Nenhuma música para ordenar.")
        return

    print("Reordenando a playlist no Spotify... Isso pode levar um momento.")
    # A API permite no máximo 100 faixas por chamada.
    # Primeiro, substituímos as 100 primeiras.
    sp.playlist_replace_items(playlist_id, sorted_track_uris[:100])
    
    # Se houver mais, as adicionamos em blocos de 100.
    if len(sorted_track_uris) > 100:
        for i in range(100, len(sorted_track_uris), 100):
            sp.playlist_add_items(playlist_id, sorted_track_uris[i:i+100])
        
    print("✨ Playlist organizada com sucesso! ✨")

def main():
    """Função principal que orquestra todo o processo."""
    try:
        sp = get_spotify_client()

        all_playlists = sp.current_user_playlists()['items']
        print("\n--- Suas Playlists ---")
        for i, p in enumerate(all_playlists):
            print(f"  {i+1} - {p['name']}")
        
        chosen_playlists_map = {} # Usaremos um dicionário para evitar repetidos
        while True:
            choice = input(f"\nEscolha uma playlist para adicionar à lista (ou pressione Enter para finalizar): ")
            if not choice:
                if not chosen_playlists_map:
                    print("Nenhuma playlist selecionada. Saindo.")
                    return
                break

            try:
                playlist_index = int(choice) - 1
                if 0 <= playlist_index < len(all_playlists):
                    # Adiciona ao dicionário para garantir que não haja repetidos
                    chosen_playlists_map[all_playlists[playlist_index]['id']] = all_playlists[playlist_index]
                    print("Playlists a serem organizadas:")
                    for p in chosen_playlists_map.values():
                        print(f"  - {p['name']}")
                else:
                    print("Número fora do intervalo. Tente novamente.")
            except ValueError:
                print("Entrada inválida. Por favor, digite um número.")
        
        chosen_playlists = list(chosen_playlists_map.values())

        chosen_keys, reverse_sort = display_menu_and_get_choices()
        if chosen_keys is None:
            print("Nenhum critério de ordenação escolhido. Saindo.")
            return

        print("\n" + "="*40)
        print("INICIANDO ORGANIZAÇÃO EM LOTE")
        print("="*40)

        for playlist in chosen_playlists:
            playlist_name = playlist['name']
            playlist_id = playlist['id']
            print(f"\n--- Processando playlist: '{playlist_name}' ---")
            
            tracks_to_sort = get_all_playlist_tracks_with_details(sp, playlist_id)
            
            sorted_tracks = sorted(
                tracks_to_sort,
                key=lambda track: tuple(track[key] for key in chosen_keys),
                reverse=reverse_sort
            )
            sorted_track_uris = [track['uri'] for track in sorted_tracks]
            
            reorder_playlist_in_spotify(sp, playlist_id, sorted_track_uris)
        
        print("\n" + "="*40)
        print("TODAS AS PLAYLISTS SELECIONADAS FORAM ORGANIZADAS!")
        print("="*40)

    except Exception as e:
        print(f"\n❌ Ocorreu um erro inesperado: {e}")
        print("   Por favor, verifique sua conexão e tente novamente.")

if __name__ == '__main__':
    main()