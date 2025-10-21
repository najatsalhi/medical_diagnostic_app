# Images pour l'Application Médicale CHU

## 📁 Dossier static/

Ce dossier contient les fichiers statiques de l'application, y compris les images de fond.

### 🏥 Image de fond CHU recommandée :

**Nom du fichier :** `chu_background.jpg`

**Caractéristiques recommandées :**
- **Résolution :** 1920x1080 px ou plus
- **Format :** JPG ou PNG
- **Taille :** Moins de 2 MB pour des performances optimales
- **Contenu :** Photo d'hôpital, CHU, ou bâtiment médical

### 🎨 Types d'images CHU suggérées :

1. **Façade d'hôpital moderne**
2. **Hall d'accueil CHU** 
3. **Couloirs médicaux professionnels**
4. **Vue aérienne d'un complexe hospitalier**
5. **Architecture médicale contemporaine**

### 📝 Comment ajouter votre image :

1. Copiez votre image dans ce dossier `static/`
2. Renommez-la `chu_background.jpg`
3. L'application utilisera automatiquement votre image

### 🔄 Images alternatives :

Si vous voulez changer le nom de l'image, modifiez cette ligne dans `templates/login.html` :

```css
background: linear-gradient(...), url('{{ url_for("static", filename="VOTRE_NOM_IMAGE.jpg") }}');
```

### 📱 Responsive :

L'image s'adaptera automatiquement à tous les écrans grâce aux propriétés CSS :
- `background-size: cover`
- `background-position: center`
