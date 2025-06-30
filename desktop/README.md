# Gamer Cred Desktop

A modern desktop companion application for the Gamer Cred Discord bot, built with Electron and designed to provide seamless gaming session tracking and statistics management.

## Features

### 🎮 **Automatic Game Detection**
- Monitors active applications to detect when games are running
- Supports popular gaming platforms (Steam, Epic, Origin, etc.)
- Automatic session tracking with real-time timer

### 📊 **Comprehensive Dashboard**
- Quick stats overview (credits, hours, games played, rank)
- Recent activity feed
- One-click session logging
- Real-time leaderboard updates

### ⏱️ **Advanced Session Tracker**
- Manual and automatic session tracking
- Pause/resume functionality
- Session duration timer
- Game detection notifications

### 🏆 **Leaderboard Integration**
- Weekly, monthly, and all-time leaderboards
- Real-time ranking updates
- User placement history

### 📈 **Personal Statistics**
- Detailed gaming history
- Game-specific statistics
- Achievement tracking
- Progress visualization

### ⚙️ **Customizable Settings**
- Auto-start tracking options
- Notification preferences
- API configuration
- Discord integration

## Installation

### Prerequisites
- Node.js (v16 or higher)
- npm or yarn
- Windows 10/11 (primary support)

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd desktop
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure environment**
   - Copy `.env.example` to `.env`
   - Update API URL and other settings as needed

4. **Run in development mode**
   ```bash
   npm run dev
   ```

5. **Build for production**
   ```bash
   npm run build-win
   ```

## Development

### Project Structure
```
desktop/
├── main.js                 # Main Electron process
├── preload.js             # Preload script for security
├── package.json           # Dependencies and scripts
├── renderer/              # Frontend application
│   ├── index.html         # Main HTML file
│   ├── styles/            # CSS files
│   │   ├── main.css       # Main styles
│   │   └── components.css # Component styles
│   └── js/                # JavaScript modules
│       ├── app.js         # Main app controller
│       ├── api.js         # API utilities
│       └── pages/         # Page-specific modules
│           ├── dashboard.js
│           ├── session-tracker.js
│           ├── leaderboard.js
│           ├── my-stats.js
│           ├── recent-activity.js
│           ├── games.js
│           └── settings.js
└── assets/                # Icons and images
```

### Key Technologies
- **Electron**: Cross-platform desktop framework
- **Vanilla JavaScript**: No framework dependencies
- **CSS3**: Modern styling with CSS Grid and Flexbox
- **Font Awesome**: Icon library
- **Inter Font**: Modern typography

### API Integration
The desktop app integrates with the existing Gamer Cred web API:
- Session logging
- User statistics
- Leaderboard data
- Game information
- Discord authentication

## Features in Detail

### Game Detection
The app uses Windows API to monitor active processes and detect gaming applications:

- **Process Monitoring**: Tracks active window processes
- **Game Database**: Pre-configured list of popular games
- **Smart Detection**: Keyword-based detection for unknown games
- **Real-time Updates**: Immediate detection and tracking

### Session Management
Comprehensive session tracking with multiple features:

- **Automatic Tracking**: Start tracking when games are detected
- **Manual Control**: Start/stop/pause/resume sessions
- **Duration Calculation**: Precise time tracking
- **Session Logging**: One-click logging to the server

### User Interface
Modern, responsive design optimized for desktop use:

- **Dark Theme**: Gaming-focused dark interface
- **Responsive Layout**: Adapts to different window sizes
- **System Tray**: Minimize to system tray for background operation
- **Notifications**: Desktop notifications for important events

### Data Synchronization
Seamless integration with the web platform:

- **Real-time Sync**: Live updates from the server
- **Offline Support**: Queue sessions when offline
- **Conflict Resolution**: Handle data conflicts gracefully
- **Caching**: Local caching for better performance

## Configuration

### Settings
The app can be configured through the settings panel:

- **API URL**: Point to your Gamer Cred server
- **Auto-tracking**: Automatically start tracking on app launch
- **Notifications**: Enable/disable desktop notifications
- **Start with Windows**: Auto-start the app on system boot

### Game Detection
Customize game detection by editing the game process list in `main.js`:

```javascript
const GAME_PROCESSES = new Set([
  'steam.exe',
  'EpicGamesLauncher.exe',
  'cs2.exe',
  // Add more games here
]);
```

## Building and Distribution

### Development Build
```bash
npm run dev
```

### Production Build
```bash
# Windows
npm run build-win

# macOS
npm run build-mac

# Linux
npm run build-linux
```

### Distribution
Built applications are available in the `dist/` folder:
- Windows: `.exe` installer
- macOS: `.dmg` file
- Linux: `.AppImage` file

## Troubleshooting

### Common Issues

1. **Game Detection Not Working**
   - Check if the game process is in the detection list
   - Verify Windows permissions
   - Restart the application

2. **API Connection Issues**
   - Verify the API URL in settings
   - Check network connectivity
   - Ensure the server is running

3. **Session Not Logging**
   - Verify Discord authentication
   - Check API response for errors
   - Ensure minimum session duration (0.1 hours)

### Debug Mode
Run with debug logging:
```bash
npm run dev -- --debug
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue on GitHub
- Join the Discord server
- Check the documentation

## Roadmap

### Planned Features
- [ ] Steam integration for automatic game detection
- [ ] Achievement tracking
- [ ] Screenshot capture
- [ ] Voice commands
- [ ] Multi-language support
- [ ] Advanced analytics
- [ ] Export functionality
- [ ] Cloud sync

### Future Enhancements
- [ ] Mobile companion app
- [ ] Social features
- [ ] Game recommendations
- [ ] Performance monitoring
- [ ] Health reminders 