# CSS Structure Documentation

## Overview

The CSS has been reorganized from a single large `style.css` file into a modular structure for better maintainability, performance, and developer experience.

## File Structure

```
website/public/
├── main.css              # Main file that imports all CSS modules
├── base.css              # Global styles (body, navbar, common elements)
├── components.css        # Reusable UI components
├── home.css              # Homepage-specific styles
├── games.css             # Games listing page styles
├── game.css              # Individual game page styles
├── user.css              # User profile page styles
├── responsive.css        # Mobile and responsive styles
└── style.css             # Original file (kept for backup)
```

## File Descriptions

### `main.css`
- **Purpose**: Imports all CSS modules in the correct order
- **Usage**: Include this file in HTML for full functionality
- **Dependencies**: All other CSS files

### `base.css`
- **Purpose**: Global styles used across all pages
- **Contains**:
  - Body and typography styles
  - Navbar and navigation
  - Common elements (cards, avatars, links)
  - Toast notifications
  - Footer

### `components.css`
- **Purpose**: Reusable UI components
- **Contains**:
  - Buttons (react buttons, submit buttons)
  - Forms and form elements
  - Tabs and tab navigation
  - Search and autocomplete
  - Stats displays
  - Game covers
  - Lists (leaderboard, activity, bonuses)

### `home.css`
- **Purpose**: Homepage-specific styles
- **Contains**:
  - Main grid layout
  - Log game form
  - Activity carousel
  - Timer widget
  - Most popular section

### `games.css`
- **Purpose**: Games listing page styles
- **Contains**:
  - Games grid layout
  - Game cards
  - Search and filter controls
  - Sorting functionality

### `game.css`
- **Purpose**: Individual game page styles
- **Contains**:
  - Game header and cover
  - Game stats and information
  - Player lists
  - Game activity
  - Game trailer section

### `user.css`
- **Purpose**: User profile page styles
- **Contains**:
  - Profile cards
  - User stats
  - Profile activity
  - Side-by-side layouts

### `responsive.css`
- **Purpose**: Mobile and responsive styles
- **Contains**:
  - Media queries for different screen sizes
  - Mobile navigation
  - Responsive layouts
  - Touch-friendly interactions

## Usage Options

### Option 1: Use Main CSS File (Recommended)
Include only `main.css` in your HTML files:
```html
<link rel="stylesheet" href="main.css">
```

### Option 2: Page-Specific Loading (Advanced)
For optimal performance, you can load only the CSS needed for each page:

**Homepage:**
```html
<link rel="stylesheet" href="base.css">
<link rel="stylesheet" href="components.css">
<link rel="stylesheet" href="home.css">
<link rel="stylesheet" href="responsive.css">
```

**Games Page:**
```html
<link rel="stylesheet" href="base.css">
<link rel="stylesheet" href="components.css">
<link rel="stylesheet" href="games.css">
<link rel="stylesheet" href="responsive.css">
```

**Game Page:**
```html
<link rel="stylesheet" href="base.css">
<link rel="stylesheet" href="components.css">
<link rel="stylesheet" href="game.css">
<link rel="stylesheet" href="responsive.css">
```

**User Page:**
```html
<link rel="stylesheet" href="base.css">
<link rel="stylesheet" href="components.css">
<link rel="stylesheet" href="user.css">
<link rel="stylesheet" href="responsive.css">
```

## Benefits

### 🚀 Performance
- **Faster loading**: Only load CSS needed for each page
- **Better caching**: Browser can cache individual files
- **Reduced file size**: No duplicate styles across pages

### 🛠️ Development
- **Easier maintenance**: Find and edit styles faster
- **Better organization**: Clear separation of concerns
- **Team collaboration**: Multiple developers can work on different files
- **Easier debugging**: Isolated styles reduce conflicts

### 📱 Responsive Design
- **Mobile-first**: Responsive styles are separate and organized
- **Better testing**: Test mobile styles independently
- **Cleaner code**: No mixing of desktop and mobile styles

## Migration Notes

- The original `style.css` file is kept as a backup
- All HTML files have been updated to use `main.css`
- No functionality has been lost in the reorganization
- All existing styles are preserved

## Future Development

When adding new styles:

1. **Global styles** → Add to `base.css`
2. **Reusable components** → Add to `components.css`
3. **Page-specific styles** → Add to appropriate page CSS file
4. **Mobile/responsive** → Add to `responsive.css`

## Troubleshooting

If styles are missing or not working:

1. Check that `main.css` is properly linked in HTML
2. Verify all CSS files exist in the `website/public/` directory
3. Check browser console for any CSS loading errors
4. Ensure the import order in `main.css` is correct

## File Sizes

- `main.css`: ~1KB (imports only)
- `base.css`: ~8KB
- `components.css`: ~12KB
- `home.css`: ~15KB
- `games.css`: ~8KB
- `game.css`: ~12KB
- `user.css`: ~6KB
- `responsive.css`: ~8KB

**Total**: ~70KB (vs original 60KB single file) 