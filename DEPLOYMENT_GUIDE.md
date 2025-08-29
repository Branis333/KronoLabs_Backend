# 🚀 KronoLabs Backend Deployment Guide

## 🔧 **Render Deployment Fix**

### **Step 1: Fix Environment Variables**

1. **Go to your Render dashboard**
2. **Select your KronoLabs service**
3. **Navigate to "Environment" tab**
4. **Set the following environment variables:**

```bash
DATABASE_URL=postgresql://postgres.xxxxx:[YOUR-PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
SECRET_KEY=your-super-secret-jwt-key-here-make-it-long-and-random
ALGORITHM=HS256
```

### **Step 2: Get Correct Supabase Connection String**

1. **Go to your Supabase dashboard**
2. **Select your project**
3. **Go to Settings → Database**
4. **Copy the "Connection string" (URI format)**
5. **Replace `[YOUR-PASSWORD]` with your actual database password**

### **Step 3: Verify Deployment**

After setting environment variables:

1. **Redeploy your Render service**
2. **Check the logs for:** `✅ Supabase connection successful!`
3. **Test the health endpoint:** `https://your-app.onrender.com/health`

### **Expected Health Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "message": "KronoLabs API is running successfully"
}
```

## 🐛 **Common Issues & Solutions**

### **Issue 1: "Tenant or user not found"**
- ❌ **Cause:** Wrong database URL or password
- ✅ **Fix:** Double-check Supabase connection string and password

### **Issue 2: "DATABASE_URL environment variable is not set"**
- ❌ **Cause:** Missing environment variable in Render
- ✅ **Fix:** Add DATABASE_URL in Render environment settings

### **Issue 3: SSL Connection Errors**
- ❌ **Cause:** SSL configuration issues
- ✅ **Fix:** Already handled in code with `sslmode=require`

## 📱 **Testing Your Deployed API**

### **1. Health Check**
```bash
curl https://your-app.onrender.com/health
```

### **2. API Documentation**
```bash
https://your-app.onrender.com/docs
```

### **3. Test Registration**
```bash
curl -X POST "https://your-app.onrender.com/register" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpassword123",
    "fname": "Test",
    "lname": "User"
  }'
```

## 🔐 **Security Notes**

1. **Never commit real environment variables to Git**
2. **Use strong, random SECRET_KEY for JWT**
3. **Keep your Supabase password secure**
4. **Enable row-level security in Supabase if needed**

## 🆘 **If Still Having Issues**

1. **Check Render logs** for specific error messages
2. **Test your Supabase connection** using a PostgreSQL client
3. **Verify your Supabase project is active** and not paused
4. **Check Supabase usage limits** (free tier limitations)

## 📞 **Support**

If you continue having issues, check:
- Render service logs
- Supabase project status
- Environment variable spelling and formatting
