# Deployment Guide - File Uploads

## 🚨 Important: File Uploads in Production

When deploying from a GitHub repository, user uploads will be **lost** on every deployment because:
- The repository is static and doesn't include user files
- Production environments are recreated from the repository
- Local file storage is ephemeral

## 🔧 Solutions

### Option 1: Cloudinary (Recommended - Free Tier)

1. **Sign up** at [cloudinary.com](https://cloudinary.com) (free tier available)
2. **Get your credentials** from the dashboard
3. **Set environment variables**:
   ```bash
   CLOUDINARY_CLOUD_NAME=your_cloud_name
   CLOUDINARY_API_KEY=your_api_key
   CLOUDINARY_API_SECRET=your_api_secret
   ```

### Option 2: ImgBB (Free Image Hosting)

1. **Get API key** from [imgbb.com](https://imgbb.com/api)
2. **Set environment variable**:
   ```bash
   IMGBB_API_KEY=your_api_key
   ```

### Option 3: AWS S3 (Paid but Reliable)

1. **Create S3 bucket**
2. **Set environment variables**:
   ```bash
   AWS_ACCESS_KEY_ID=your_access_key
   AWS_SECRET_ACCESS_KEY=your_secret_key
   AWS_S3_BUCKET=your_bucket_name
   ```

## 🎯 How It Works

The app automatically detects which service to use based on environment variables:

1. **If Cloudinary is configured** → Uses Cloudinary
2. **If ImgBB is configured** → Uses ImgBB (images only)
3. **If neither is configured** → Falls back to local storage (not recommended for production)

## 📁 Local Development

For local development, files are saved to:
```
website/public/uploads/backgrounds/images/
website/public/uploads/backgrounds/videos/
```

This directory is **ignored by Git** (see `.gitignore`).

## 🔄 Migration

If you have existing local uploads and want to move to cloud storage:

1. **Set up cloud storage** (see options above)
2. **Upload existing files** to cloud storage
3. **Update database URLs** to point to cloud URLs

## ⚠️ Important Notes

- **Backup your uploads** before deploying
- **Test cloud storage** in development first
- **Monitor storage usage** (especially with free tiers)
- **Consider costs** for high-volume applications

## 🚀 Quick Setup

For immediate deployment with free cloud storage:

1. Sign up for Cloudinary (free tier)
2. Add environment variables to your deployment platform
3. Deploy - uploads will automatically use cloud storage 