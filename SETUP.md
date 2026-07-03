# Jarvis Finance — Setup environnement

Guide pour recréer un environnement de développement iso-fonctionnel, incluant Python, Claude Code CLI, plugins et hooks.

---

## 1. Prérequis système

- **Python 3.12+**
- **Git**
- **Node.js** (requis par Claude Code CLI)
- **Windows 10/11** (les hooks PowerShell sont Windows-only)

---

## 2. Projet Python

```bash
git clone https://github.com/do4fun/jarvis-finance.git
cd jarvis-finance
pip install -r requirements.txt
cp .env.example .env
# Éditer .env : renseigner ANTHROPIC_API_KEY
```

**Dépendances Python** (`requirements.txt`) :
```
anthropic>=0.52.0
pydantic>=2.0.0
python-dotenv>=1.0.0
```

---

## 3. Claude Code CLI

```bash
npm install -g @anthropic-ai/claude-code
```

Vérification : `claude --version` → `2.1.196 (Claude Code)` (ou supérieur)

---

## 4. Plugins Claude Code

Les plugins sont installés via `claude plugin install`. Les scopes `user` s'installent une fois pour tous les projets ; les scopes `local` doivent être réinstallés dans le répertoire du projet.

### 4.1 Plugin Superpowers (scope : user)

```bash
claude plugin install superpowers@claude-plugins-official
```

Plugin officiel Anthropic — fournit les skills de workflow (brainstorming, code-review, debugging, plan mode, etc.).

### 4.2 Plugin Deep Project (scope : local — à installer dans le projet)

```bash
# Depuis c:\dev\jarvis-finance
claude plugin install deep-project@piercelamb-plugins
```

Marketplace custom — ajouter d'abord la marketplace :

```bash
claude plugin marketplace add piercelamb-plugins github:piercelamb/deep-project
```

### 4.3 Plugin Claude Mem (scope : local — à installer dans le projet)

```bash
claude plugin marketplace add thedotmack github:thedotmack/claude-mem
claude plugin install claude-mem@thedotmack
```

### 4.4 Plugins désactivés (installés mais non actifs)

```bash
# Optionnel — peuvent être installés sans être activés
claude plugin install vercel@claude-plugins-official        # scope local, projet Vercel uniquement
claude plugin install claude-md-management@claude-plugins-official  # scope user
```

---

## 5. Configuration Claude Code (`~/.claude/settings.json`)

Créer ou fusionner `%USERPROFILE%\.claude\settings.json` :

```json
{
  "model": "sonnet",
  "effortLevel": "medium",
  "autoUpdatesChannel": "latest",
  "theme": "dark",
  "agentPushNotifEnabled": true,
  "enabledPlugins": {
    "superpowers@claude-plugins-official": true,
    "deep-project@piercelamb-plugins": true
  },
  "extraKnownMarketplaces": {
    "thedotmack": {
      "source": { "source": "github", "repo": "thedotmack/claude-mem" }
    },
    "piercelamb-plugins": {
      "source": { "source": "github", "repo": "piercelamb/deep-project" }
    }
  },
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "powershell -NoProfile -NonInteractive -File C:\\Users\\<USER>\\.claude\\scripts\\notify-task-done.ps1",
            "timeout": 10,
            "async": true
          }
        ]
      }
    ],
    "PostCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "powershell -NoProfile -NonInteractive -File C:\\Users\\<USER>\\.claude\\scripts\\save-compact-history.ps1",
            "timeout": 30,
            "async": true
          }
        ]
      }
    ]
  }
}
```

> Remplacer `<USER>` par le nom d'utilisateur Windows.

---

## 6. Scripts PowerShell (`~/.claude/scripts/`)

Créer le répertoire `%USERPROFILE%\.claude\scripts\` et y placer les deux scripts suivants.

### `notify-task-done.ps1` — Notification Windows à la fin de chaque tâche

Déclenché par le hook `Stop`. Affiche une notification Toast Windows (ou une bulle system tray en fallback) quand Claude termine.

```powershell
$ErrorActionPreference = 'SilentlyContinue'

try {
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
    $xml.LoadXml('<toast><visual><binding template="ToastGeneric"><text>Claude Code</text><text>Tâche terminée ✓</text></binding></visual></toast>')
    $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Claude Code').Show($toast)
} catch {
    Add-Type -AssemblyName System.Windows.Forms
    $n = New-Object System.Windows.Forms.NotifyIcon
    $n.Icon = [System.Drawing.SystemIcons]::Information
    $n.Visible = $true
    $n.BalloonTipTitle = 'Claude Code'
    $n.BalloonTipText = 'Tâche terminée !'
    $n.BalloonTipIcon = 'Info'
    $n.ShowBalloonTip(5000)
    Start-Sleep -Milliseconds 800
    $n.Dispose()
}
```

### `save-compact-history.ps1` — Sauvegarde des résumés de contexte compressé

Déclenché par le hook `PostCompact`. Sauvegarde chaque résumé de compaction de contexte sur une branche orpheline `compact-history` du dépôt git courant, puis la pousse vers l'origin.

```powershell
$ErrorActionPreference = 'SilentlyContinue'

$raw  = [Console]::In.ReadToEnd()
$data = $raw | ConvertFrom-Json

$rawSummary = if ($data.compact_summary) { $data.compact_summary }
              elseif ($data.summary)     { $data.summary }
              else                       { $raw }

if ($rawSummary -match '(?s)<summary>(.*)</summary>') {
    $body = $Matches[1].Trim()
} else {
    $body = $rawSummary.Trim()
}

$timestamp    = Get-Date -Format 'yyyy-MM-dd HH:mm'
$fileStamp    = Get-Date -Format 'yyyy-MM-dd_HH-mm'
$root         = git rev-parse --show-toplevel 2>$null
$branch       = git -C $root rev-parse --abbrev-ref HEAD 2>$null
$projectName  = Split-Path -Leaf $root
$worktreePath = "$root/.compact-worktree"
$histBranch   = "compact-history"

if (-not $root) { exit 0 }

$header = @"
# Compact History — $timestamp

**Projet :** $projectName
**Branche :** $branch
**Trigger :** $($data.trigger ?? 'auto')

---

"@

$content = $header + $body

$branchExists = git -C $root branch --list $histBranch
if (-not $branchExists) {
    $emptyTree  = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    $commitHash = git -C $root commit-tree $emptyTree -m "init: compact-history [auto]"
    git -C $root branch $histBranch $commitHash
}

if (-not (Test-Path $worktreePath)) {
    git -C $root worktree add $worktreePath $histBranch 2>&1 | Out-Null
}

$file = "$worktreePath/$fileStamp.md"
Set-Content -Path $file -Value $content -Encoding utf8

git -C $worktreePath add "$fileStamp.md"
git -C $worktreePath commit -m "docs: compact $fileStamp [auto]"

git -C $root push origin $histBranch 2>&1 | Out-Null
```

---

## 7. Vérification

```bash
# Python
python -c "import anthropic, pydantic, dotenv; print('OK')"

# Claude Code
claude --version

# Plugins actifs (dans le répertoire du projet)
claude plugin list
```

Résultat attendu pour `claude plugin list` dans `jarvis-finance` :

```
superpowers@claude-plugins-official   6.x.x   user    ✓ enabled
deep-project@piercelamb-plugins       0.x.x   local   ✓ enabled
claude-mem@thedotmack                 13.x.x  local   ✓ enabled
```
