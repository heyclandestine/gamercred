-- Migration script to update game_screenshots table to use base64 image data instead of image_url
-- Run this script in your PostgreSQL database

-- Add new columns if they don't exist
DO $$
BEGIN
    -- Check if image_data column exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'game_screenshots' 
        AND column_name = 'image_data'
    ) THEN
        ALTER TABLE game_screenshots ADD COLUMN image_data TEXT;
        RAISE NOTICE 'Added image_data column';
    ELSE
        RAISE NOTICE 'image_data column already exists';
    END IF;
    
    -- Check if image_filename column exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'game_screenshots' 
        AND column_name = 'image_filename'
    ) THEN
        ALTER TABLE game_screenshots ADD COLUMN image_filename VARCHAR;
        RAISE NOTICE 'Added image_filename column';
    ELSE
        RAISE NOTICE 'image_filename column already exists';
    END IF;
    
    -- Check if image_mime_type column exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'game_screenshots' 
        AND column_name = 'image_mime_type'
    ) THEN
        ALTER TABLE game_screenshots ADD COLUMN image_mime_type VARCHAR;
        RAISE NOTICE 'Added image_mime_type column';
    ELSE
        RAISE NOTICE 'image_mime_type column already exists';
    END IF;
END $$;

-- Remove old image_url column if it exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'game_screenshots' 
        AND column_name = 'image_url'
    ) THEN
        ALTER TABLE game_screenshots DROP COLUMN image_url;
        RAISE NOTICE 'Removed image_url column';
    ELSE
        RAISE NOTICE 'image_url column already removed';
    END IF;
END $$;

-- Display the final table structure
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'game_screenshots' 
ORDER BY ordinal_position; 