from collections import deque
from pathlib import Path
import random

try:
    import pygame
except ImportError as erreur:
    raise SystemExit("Pygame manque. Lance le jeu avec : .venv/bin/python labyrinthe_graphique.py") from erreur


DIRECTIONS = {"z": (-1, 0), "s": (1, 0), "q": (0, -1), "d": (0, 1)}
DIRECTION_PAR_DEPLACEMENT = {deplacement: nom for nom, deplacement in DIRECTIONS.items()}
NOMS_DIRECTIONS = {"z": "haut", "s": "bas", "q": "gauche", "d": "droite"}
IMAGES = Path(__file__).resolve().parent / "images"
TAILLE_MAX = 41

FOND = (25, 36, 29)
PANNEAU = (33, 47, 37)
TEXTE = (239, 237, 218)
TEXTE_FAIBLE = (169, 183, 162)
VERT = (142, 188, 117)
OR = (245, 192, 99)
CORAIL = (226, 133, 104)


def generer_labyrinthe(taille):
    if taille < 5 or taille % 2 == 0:
        raise ValueError("La taille doit etre un nombre impair d'au moins 5.")

    cases = [["#" for _ in range(taille)] for _ in range(taille)]
    depart = (1, 1)
    cases[1][1] = "."
    pile = [depart]

    while pile:
        ligne, colonne = pile[-1]
        voisins = []
        for delta_ligne, delta_colonne in DIRECTIONS.values():
            nouvelle_ligne = ligne + 2 * delta_ligne
            nouvelle_colonne = colonne + 2 * delta_colonne
            if (
                1 <= nouvelle_ligne < taille - 1
                and 1 <= nouvelle_colonne < taille - 1
                and cases[nouvelle_ligne][nouvelle_colonne] == "#"
            ):
                voisins.append((nouvelle_ligne, nouvelle_colonne))

        if not voisins:
            pile.pop()
            continue

        suivante = random.choice(voisins)
        mur = ((ligne + suivante[0]) // 2, (colonne + suivante[1]) // 2)
        cases[mur[0]][mur[1]] = "."
        cases[suivante[0]][suivante[1]] = "."
        pile.append(suivante)

    cases[1][1] = "S"
    cases[taille - 2][taille - 2] = "E"
    return tuple("".join(ligne) for ligne in cases)


def trouver_case(carte, symbole):
    for ligne, cases in enumerate(carte):
        colonne = cases.find(symbole)
        if colonne != -1:
            return ligne, colonne
    raise ValueError(f"La carte ne contient pas la case {symbole}.")


def trouver_chemin(carte, depart, arrivee):
    file = deque([depart])
    precedents = {depart: None}
    while file:
        position = file.popleft()
        if position == arrivee:
            break
        for deplacement in DIRECTIONS.values():
            voisin = (position[0] + deplacement[0], position[1] + deplacement[1])
            if (
                0 <= voisin[0] < len(carte)
                and 0 <= voisin[1] < len(carte[0])
                and carte[voisin[0]][voisin[1]] != "#"
                and voisin not in precedents
            ):
                precedents[voisin] = position
                file.append(voisin)

    if arrivee not in precedents:
        return None
    chemin = []
    position = arrivee
    while position is not None:
        chemin.append(position)
        position = precedents[position]
    return list(reversed(chemin))


class JeuLabyrinthe:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Le grand labyrinthe")
        self.ecran = pygame.display.set_mode((760, 820), pygame.RESIZABLE)
        self.horloge = pygame.time.Clock()
        self.police = pygame.font.Font(None, 25)
        self.police_petite = pygame.font.Font(None, 19)
        self.police_titre = pygame.font.Font(None, 44)
        self.police_chiffre = pygame.font.Font(None, 37)
        self.images = self.charger_images()
        self.cache_textures = {}
        self.rectangles_boutons = {}
        self.direction = "s"
        self.creer_niveau(1)

    def charger_images(self):
        noms = {
            "herbe": "herbe.jpg", "mur": "mur.jpg",
            "normal": "normal.png", "normal_z": "normal_arriere.png",
            "normal_q": "normal_gauche.png", "normal_d": "normal_droite.png",
            "marche_s1": "marche_avant1.png", "marche_s2": "marche_avant2.png",
            "marche_z1": "marche_arriere1.png", "marche_z2": "marche_arriere2.png",
            "marche_q1": "marche_gauche1.png", "marche_q2": "marche_gauche2.png",
            "marche_d1": "marche_droite1.png", "marche_d2": "marche_droite2.png",
        }
        images = {}
        for nom, fichier in noms.items():
            dossier = IMAGES if nom in ("herbe", "mur") else IMAGES / "Player"
            chemin = dossier / fichier
            try:
                image = pygame.image.load(str(chemin))
                images[nom] = image.convert() if nom in ("herbe", "mur") else image.convert_alpha()
            except (FileNotFoundError, pygame.error) as erreur:
                print(f"Image ignoree ({fichier}) : {erreur}")
        return images

    def creer_niveau(self, niveau):
        self.niveau = niveau
        taille = min(9 + 2 * (niveau - 1), TAILLE_MAX)
        self.carte = generer_labyrinthe(taille)
        self.depart = trouver_case(self.carte, "S")
        self.sortie = trouver_case(self.carte, "E")
        self.joueur = self.depart
        self.mouvements = 0
        self.chemin_indice = None
        self.animation = None
        self.victoire = False
        chemin = trouver_chemin(self.carte, self.depart, self.sortie)
        self.chemin_minimum = len(chemin) - 1
        self.message = "Trouve la porte doree. ZQSD ou les fleches pour bouger."

    def texture(self, nom, taille):
        cle = (nom, taille)
        if cle not in self.cache_textures and nom in self.images:
            self.cache_textures[cle] = pygame.transform.scale(self.images[nom], (taille, taille))
        return self.cache_textures.get(cle)

    def ecrire(self, texte, position, police=None, couleur=TEXTE):
        image_texte = (police or self.police).render(str(texte), True, couleur)
        self.ecran.blit(image_texte, position)

    def bouton(self, nom, libelle, rectangle, accent=False, desactive=False):
        survole = rectangle.collidepoint(pygame.mouse.get_pos())
        couleur = VERT if accent else (68, 87, 67)
        if desactive:
            couleur = (55, 67, 55)
        elif survole:
            couleur = (164, 202, 132) if accent else (83, 106, 81)
        pygame.draw.rect(self.ecran, couleur, rectangle, border_radius=5)
        pygame.draw.rect(self.ecran, (186, 218, 156) if survole else (255, 255, 255), rectangle, 1, border_radius=5)
        couleur_texte = FOND if accent and not desactive else TEXTE
        rendu = self.police_petite.render(libelle, True, couleur_texte)
        self.ecran.blit(rendu, rendu.get_rect(center=rectangle.center))
        if not desactive:
            self.rectangles_boutons[nom] = rectangle

    def dessiner_plateau(self, plateau):
        pygame.draw.rect(self.ecran, (15, 23, 18), plateau, border_radius=6)
        taille_carte = len(self.carte)
        tuile = max(6, min(44, (plateau.width - 28) // taille_carte, (plateau.height - 28) // taille_carte))
        largeur_carte = taille_carte * tuile
        origine_x = plateau.x + (plateau.width - largeur_carte) // 2
        origine_y = plateau.y + (plateau.height - largeur_carte) // 2
        herbe = self.texture("herbe", tuile)
        mur = self.texture("mur", tuile)

        for ligne, cases in enumerate(self.carte):
            for colonne, case in enumerate(cases):
                rectangle = pygame.Rect(origine_x + colonne * tuile, origine_y + ligne * tuile, tuile, tuile)
                image = mur if case == "#" else herbe
                if image:
                    self.ecran.blit(image, rectangle)
                else:
                    pygame.draw.rect(self.ecran, (76, 80, 61) if case == "#" else (93, 132, 76), rectangle)

        porte_x = origine_x + self.sortie[1] * tuile
        porte_y = origine_y + self.sortie[0] * tuile
        largeur_porte = max(8, int(tuile * 0.62))
        porte = pygame.Rect(porte_x + (tuile - largeur_porte) // 2, porte_y + tuile // 5, largeur_porte, tuile * 4 // 5)
        pygame.draw.rect(self.ecran, OR, porte, border_radius=3)
        pygame.draw.rect(self.ecran, (100, 67, 39), porte.inflate(-tuile // 4, -tuile // 5), border_radius=2)

        if self.chemin_indice and len(self.chemin_indice) > 1:
            calque = pygame.Surface((largeur_carte, largeur_carte), pygame.SRCALPHA)
            points = [(colonne * tuile + tuile // 2, ligne * tuile + tuile // 2) for ligne, colonne in self.chemin_indice]
            pygame.draw.lines(calque, (255, 211, 106, 165), False, points, max(3, tuile // 5))
            self.ecran.blit(calque, (origine_x, origine_y))

        ligne, colonne = self.joueur
        if self.animation:
            depart, arrivee, debut = self.animation
            progression = min(1.0, (pygame.time.get_ticks() - debut) / 115)
            ligne = depart[0] + (arrivee[0] - depart[0]) * progression
            colonne = depart[1] + (arrivee[1] - depart[1]) * progression
            if progression >= 1:
                self.animation = None
                if self.joueur == self.sortie:
                    self.victoire = True
                    self.message = f"Sortie en {self.mouvements} mouvements. Chemin minimal : {self.chemin_minimum}."

        marge_sprite = tuile * 0.08
        taille_sprite = max(1, int(tuile - marge_sprite * 2))
        if self.animation:
            nom_sprite = f"marche_{self.direction}{(pygame.time.get_ticks() // 90) % 2 + 1}"
        else:
            nom_sprite = f"normal_{self.direction}" if self.direction != "s" else "normal"
        sprite = self.images.get(nom_sprite)
        if sprite:
            sprite = pygame.transform.scale(sprite, (taille_sprite, taille_sprite))
            self.ecran.blit(sprite, (origine_x + colonne * tuile + marge_sprite, origine_y + ligne * tuile + marge_sprite))
        else:
            pygame.draw.circle(self.ecran, CORAIL, (int(origine_x + colonne * tuile + tuile / 2), int(origine_y + ligne * tuile + tuile / 2)), max(4, tuile // 3))

        pygame.draw.rect(self.ecran, (77, 97, 72), plateau, 1, border_radius=6)

    def dessiner_panneau(self, plateau):
        x = plateau.right + 22
        largeur = max(210, self.ecran.get_width() - x - 28)
        self.rectangles_boutons = {}
        self.ecrire("LE GRAND LABYRINTHE", (x, 26), self.police_titre)
        self.ecrire("UNE SORTIE, UN NOUVEAU CHEMIN", (x + 2, 70), self.police_petite, VERT)
        self.ecrire(f"NIVEAU {self.niveau}", (x, 117), self.police, OR)
        self.ecrire(f"Carte : {len(self.carte)} x {len(self.carte)}", (x, 146), self.police_petite, TEXTE_FAIBLE)

        statistiques = pygame.Rect(x, 184, largeur, 70)
        pygame.draw.rect(self.ecran, PANNEAU, statistiques, border_radius=5)
        self.ecrire("MOUVEMENTS", (x + 14, 194), self.police_petite, TEXTE_FAIBLE)
        self.ecrire(self.mouvements, (x + 14, 216), self.police_chiffre)
        self.ecrire("MINIMUM", (x + largeur // 2 + 8, 194), self.police_petite, TEXTE_FAIBLE)
        self.ecrire(self.chemin_minimum, (x + largeur // 2 + 8, 216), self.police_chiffre, OR)

        y = 270
        for ligne in self.message.split("\n"):
            self.ecrire(ligne, (x, y), self.police_petite, TEXTE_FAIBLE)
            y += 22

        y = 322
        hauteur_bouton = 40
        self.bouton("indice", "Indice du chemin", pygame.Rect(x, y, largeur, hauteur_bouton), accent=True, desactive=self.victoire)
        y += 49
        self.bouton("nouveau", "Nouveau labyrinthe", pygame.Rect(x, y, largeur, hauteur_bouton))
        y += 49
        if self.victoire:
            self.bouton("suivant", "Niveau suivant  >", pygame.Rect(x, y, largeur, hauteur_bouton), accent=True)
            y += 54

        self.ecrire("DEPLACEMENT", (x, y + 3), self.police_petite, TEXTE_FAIBLE)
        y += 28
        taille = 42
        milieu = x + largeur // 2
        commandes = {
            "haut": pygame.Rect(milieu - taille // 2, y, taille, taille),
            "gauche": pygame.Rect(milieu - taille - 5, y + taille + 5, taille, taille),
            "bas": pygame.Rect(milieu - taille // 2, y + taille + 5, taille, taille),
            "droite": pygame.Rect(milieu + 5, y + taille + 5, taille, taille),
        }
        for nom, rectangle in commandes.items():
            symbole = {"haut": "^", "gauche": "<", "bas": "v", "droite": ">"}[nom]
            self.bouton(nom, symbole, rectangle)
        y += taille * 2 + 22
        self.ecrire("Fleches ou ZQSD", (x, y), self.police_petite, TEXTE_FAIBLE)
        self.ecrire("H : indice  |  Echap : quitter", (x, y + 22), self.police_petite, TEXTE_FAIBLE)

    def dessiner(self):
        largeur, hauteur = self.ecran.get_size()
        self.ecran.fill(FOND)
        for y in range(0, hauteur, 54):
            pygame.draw.line(self.ecran, (28, 40, 31), (0, y), (largeur, y), 1)
        plateau = pygame.Rect(28, 112, max(340, largeur - 390), max(400, hauteur - 140))
        self.dessiner_plateau(plateau)
        self.dessiner_panneau(plateau)
        pygame.display.flip()

    def deplacer(self, direction):
        if self.victoire or self.animation:
            return
        delta_ligne, delta_colonne = DIRECTIONS[direction]
        prochaine_case = (self.joueur[0] + delta_ligne, self.joueur[1] + delta_colonne)
        if self.carte[prochaine_case[0]][prochaine_case[1]] == "#":
            self.message = "Un mur bloque le passage. Essaie une autre direction."
            return
        ancienne_case = self.joueur
        self.joueur = prochaine_case
        self.direction = direction
        self.mouvements += 1
        self.chemin_indice = None
        self.animation = (ancienne_case, prochaine_case, pygame.time.get_ticks())
        self.message = "Continue jusqu'a la porte doree."

    def donner_indice(self):
        if self.victoire:
            return
        self.chemin_indice = trouver_chemin(self.carte, self.joueur, self.sortie)
        if len(self.chemin_indice) < 2:
            return
        prochaine_case = self.chemin_indice[1]
        delta = (prochaine_case[0] - self.joueur[0], prochaine_case[1] - self.joueur[1])
        direction = DIRECTION_PAR_DEPLACEMENT[delta]
        self.message = f"Chemin minimal : commence par aller vers {NOMS_DIRECTIONS[direction]}."

    def cliquer(self, position):
        for nom, rectangle in self.rectangles_boutons.items():
            if rectangle.collidepoint(position):
                if nom in ("haut", "bas", "gauche", "droite"):
                    direction = {"haut": "z", "bas": "s", "gauche": "q", "droite": "d"}[nom]
                    self.deplacer(direction)
                elif nom == "indice":
                    self.donner_indice()
                elif nom == "nouveau":
                    self.creer_niveau(self.niveau)
                elif nom == "suivant":
                    self.creer_niveau(self.niveau + 1)
                return

    def gerer_evenement(self, evenement):
        if evenement.type == pygame.QUIT:
            return False
        if evenement.type == pygame.VIDEORESIZE:
            self.ecran = pygame.display.get_surface()
        elif evenement.type == pygame.KEYDOWN:
            if evenement.key == pygame.K_ESCAPE:
                return False
            if evenement.key == pygame.K_h:
                self.donner_indice()
            elif self.victoire and evenement.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.creer_niveau(self.niveau + 1)
            else:
                touches = {
                    pygame.K_UP: "z", pygame.K_z: "z", pygame.K_w: "z",
                    pygame.K_DOWN: "s", pygame.K_s: "s",
                    pygame.K_LEFT: "q", pygame.K_q: "q", pygame.K_a: "q",
                    pygame.K_RIGHT: "d", pygame.K_d: "d",
                }
                if evenement.key in touches:
                    self.deplacer(touches[evenement.key])
        elif evenement.type == pygame.MOUSEBUTTONDOWN and evenement.button == 1:
            self.cliquer(evenement.pos)
        return True

    def jouer(self):
        actif = True
        while actif:
            for evenement in pygame.event.get():
                actif = self.gerer_evenement(evenement) and actif
            self.dessiner()
            self.horloge.tick(60)
        pygame.quit()


def main():
    JeuLabyrinthe().jouer()


if __name__ == "__main__":
    main()