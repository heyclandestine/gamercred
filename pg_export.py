
import json

# Load the existing export
with open('database_export.json', 'r') as f:
    data = json.load(f)

# Create a structure that's more compatible with Postgres admin tools
pg_export = {
    "Servers": [
        {
            "Name": "GamerCredServer",
            "Group": "Servers",
            "Port": 5432,
            "Username": "postgres",
            "Host": "localhost",
            "SSLMode": "prefer",
            "MaintenanceDB": "postgres",
            "Databases": {
                "gamer_cred": {
                    "Tables": {
                        "public": {
                            "games": {
                                "Columns": [
                                    {"name": "id", "type": "integer", "primary_key": True},
                                    {"name": "name", "type": "text"},
                                    {"name": "credits_per_hour", "type": "float"},
                                    {"name": "added_by", "type": "bigint"}
                                ],
                                "Data": []
                            },
                            "user_stats": {
                                "Columns": [
                                    {"name": "id", "type": "integer", "primary_key": True},
                                    {"name": "user_id", "type": "bigint"},
                                    {"name": "total_credits", "type": "float"}
                                ],
                                "Data": []
                            },
                            "gaming_sessions": {
                                "Columns": [
                                    {"name": "id", "type": "integer", "primary_key": True},
                                    {"name": "user_id", "type": "bigint"},
                                    {"name": "game_id", "type": "integer"},
                                    {"name": "hours", "type": "float"},
                                    {"name": "credits_earned", "type": "float"},
                                    {"name": "timestamp", "type": "timestamp"}
                                ],
                                "Data": []
                            }
                        }
                    }
                }
            }
        }
    ]
}

# Populate the data
for game in data['games']:
    pg_export["Servers"][0]["Databases"]["gamer_cred"]["Tables"]["public"]["games"]["Data"].append([
        game["id"],
        game["name"],
        game["credits_per_hour"],
        game["added_by"]
    ])

for stat in data['user_stats']:
    pg_export["Servers"][0]["Databases"]["gamer_cred"]["Tables"]["public"]["user_stats"]["Data"].append([
        stat["id"],
        stat["user_id"],
        stat["total_credits"]
    ])

for session in data['gaming_sessions']:
    pg_export["Servers"][0]["Databases"]["gamer_cred"]["Tables"]["public"]["gaming_sessions"]["Data"].append([
        session["id"],
        session["user_id"],
        session["game_id"],
        session["hours"],
        session["credits_earned"],
        session["timestamp"] or "2025-01-01T00:00:00"
    ])

# Save as a new file
with open('postgres_admin_export.json', 'w') as f:
    json.dump(pg_export, f, indent=2)

print("✅ Created postgres_admin_export.json with a format compatible with Postgres admin tools")
print("This file includes the 'Server' attribute that your tool is looking for")
