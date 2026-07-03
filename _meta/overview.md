---
type: meta
title: "Overview"
updated: 2026-07-03T00:40:00
---

# jarvis-debate — Vue d'ensemble

Système de débat multi-agents **domain-agnostic** : le protocole (rounds, buffers,
injection croisée, argument graph, consensus pondéré) est entièrement séparé du contenu
métier. Le domaine finance (`domains/finance/`) sert d'exemple d'implémentation.

## Idée centrale

Plusieurs agents IA spécialisés (personas configurables) débattent d'une question à travers
un pipeline structuré en 7 phases (voir [[debate-pipeline]]). Le débat produit un rapport de
synthèse structuré, avec une décision arbitrée par un score de consensus pondéré par la
fiabilité historique de chaque agent — pas un simple vote majoritaire.

## Les trois piliers ajoutés récemment

1. **Consensus formel** ([[consensus]], [[001-yin-2025-consensus-formulas]]) — remplace
   l'heuristique ad-hoc précédente par les formules mathématiques de Yin 2025 : stance par
   agent, score de consensus normalisé, seuil d'acceptation configurable, apprentissage du
   poids de confiance dans le temps.
2. **Preuves et crédibilité** ([[evidence]]) — chaque claim de l'argument graph peut citer
   des preuves (`Evidence`), notées par type de source et fraîcheur, agrégées en un score
   de crédibilité par argument.
3. **Recherche web économe** ([[research]], [[003-web-research-single-anchor]]) — les
   agents peuvent débattre sur la base de données actuelles, sans faire exploser le coût en
   tokens : une seule recherche par débat, validée indépendamment avant d'atteindre le
   contexte des agents.

## Pour aller plus loin

- Démarrer par [[debate-pipeline]] pour comprendre le déroulé complet.
- [[index]] liste toutes les pages du wiki.
- Le code source fait toujours foi en cas de divergence — ce wiki documente, il ne remplace
  pas la lecture du code pour une modification réelle.
