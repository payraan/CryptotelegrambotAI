#!/usr/bin/env python3
"""
TNT Plans Migration - سیستم محدودیت و پلن‌های جدید
"""
import os
import sys
from datetime import datetime

def get_database_connection():
    """Smart database connection"""
    database_url = os.getenv("DATABASE_URL")
    
    if database_url and database_url.startswith("postgres"):
        # Production: PostgreSQL
        print("🐘 Connecting to PostgreSQL...")
        try:
            import psycopg2
            conn = psycopg2.connect(database_url)
            return conn, "postgresql", psycopg2
        except ImportError:
            print("❌ psycopg2 not available")
            sys.exit(1)
    else:
        # Development: SQLite
        print("🗄️ Connecting to SQLite...")
        import sqlite3
        conn = sqlite3.connect('bot_database.db')
        return conn, "sqlite", sqlite3

def execute_sql_safe(cursor, sql, params=None, description="SQL operation"):
    """Safe SQL execution with error handling"""
    try:
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        print(f"✅ {description}")
        return True
    except Exception as e:
        print(f"⚠️ {description}: {str(e)[:100]}")
        return False

def tnt_plans_migration():
    """Migration برای سیستم TNT Plans"""
    
    print("🚀 Starting TNT Plans Migration...")
    print("=" * 50)
    
    conn, db_type, db_module = get_database_connection()
    cursor = conn.cursor()
    
    try:
        print(f"📊 Database Type: {db_type}")
        
        # Step 1: اضافه کردن ستون plan_type جدید به users
        print("\n📝 Step 1: Adding TNT plan columns to users...")
        
        if db_type == "postgresql":
            # PostgreSQL syntax
            new_columns = [
                ("tnt_plan_type", "ALTER TABLE users ADD COLUMN tnt_plan_type TEXT DEFAULT 'FREE'"),
                ("tnt_monthly_limit", "ALTER TABLE users ADD COLUMN tnt_monthly_limit INTEGER DEFAULT 0"),
                ("tnt_hourly_limit", "ALTER TABLE users ADD COLUMN tnt_hourly_limit INTEGER DEFAULT 0"),
                ("tnt_plan_start", "ALTER TABLE users ADD COLUMN tnt_plan_start TIMESTAMP"),
                ("tnt_plan_end", "ALTER TABLE users ADD COLUMN tnt_plan_end TIMESTAMP")
            ]
        else:
            # SQLite syntax
            new_columns = [
                ("tnt_plan_type", "ALTER TABLE users ADD COLUMN tnt_plan_type TEXT DEFAULT 'FREE'"),
                ("tnt_monthly_limit", "ALTER TABLE users ADD COLUMN tnt_monthly_limit INTEGER DEFAULT 0"),
                ("tnt_hourly_limit", "ALTER TABLE users ADD COLUMN tnt_hourly_limit INTEGER DEFAULT 0"),
                ("tnt_plan_start", "ALTER TABLE users ADD COLUMN tnt_plan_start TIMESTAMP"),
                ("tnt_plan_end", "ALTER TABLE users ADD COLUMN tnt_plan_end TIMESTAMP")
            ]
        
        for column_name, sql in new_columns:
            execute_sql_safe(cursor, sql, description=f"Adding {column_name} column")
        
        # Step 2: ایجاد جدول tnt_usage_tracking
        print("\n📊 Step 2: Creating TNT usage tracking table...")
        
        if db_type == "postgresql":
            usage_table_sql = """
                CREATE TABLE IF NOT EXISTS tnt_usage_tracking (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    usage_date DATE NOT NULL,
                    usage_hour INTEGER NOT NULL,
                    analysis_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id, usage_date, usage_hour)
                )
            """
        else:
            usage_table_sql = """
                CREATE TABLE IF NOT EXISTS tnt_usage_tracking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    usage_date DATE NOT NULL,
                    usage_hour INTEGER NOT NULL,
                    analysis_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(user_id, usage_date, usage_hour)
                )
            """
        
        execute_sql_safe(cursor, usage_table_sql, description="Creating tnt_usage_tracking table")
        
        # Step 3: ایجاد جدول tnt_plans
        print("\n💎 Step 3: Creating TNT plans configuration table...")
        
        if db_type == "postgresql":
            plans_table_sql = """
                CREATE TABLE IF NOT EXISTS tnt_plans (
                    id SERIAL PRIMARY KEY,
                    plan_name TEXT UNIQUE NOT NULL,
                    plan_display_name TEXT NOT NULL,
                    price_usd DECIMAL(10,2) NOT NULL,
                    monthly_limit INTEGER NOT NULL,
                    hourly_limit INTEGER NOT NULL,
                    vip_access BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
        else:
            plans_table_sql = """
                CREATE TABLE IF NOT EXISTS tnt_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_name TEXT UNIQUE NOT NULL,
                    plan_display_name TEXT NOT NULL,
                    price_usd REAL NOT NULL,
                    monthly_limit INTEGER NOT NULL,
                    hourly_limit INTEGER NOT NULL,
                    vip_access BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
        
        execute_sql_safe(cursor, plans_table_sql, description="Creating tnt_plans table")
        
        # Step 4: اضافه کردن پلن‌های پیش‌فرض
        print("\n🎯 Step 4: Adding default TNT plans...")
        
        default_plans = [
            ('FREE', 'رایگان', 0.00, 0, 0, False),
            ('TNT_MINI', 'TNT MINI', 6.00, 60, 2, False),
            ('TNT_PLUS', 'TNT PLUS+', 10.00, 150, 4, False),
            ('TNT_MAX', 'TNT MAX', 22.00, 400, 8, True)
        ]
        
        for plan_name, display_name, price, monthly_limit, hourly_limit, vip_access in default_plans:
            if db_type == "postgresql":
                insert_sql = """
                    INSERT INTO tnt_plans (plan_name, plan_display_name, price_usd, monthly_limit, hourly_limit, vip_access)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (plan_name) DO UPDATE SET
                    plan_display_name = EXCLUDED.plan_display_name,
                    price_usd = EXCLUDED.price_usd,
                    monthly_limit = EXCLUDED.monthly_limit,
                    hourly_limit = EXCLUDED.hourly_limit,
                    vip_access = EXCLUDED.vip_access,
                    updated_at = CURRENT_TIMESTAMP
                """
            else:
                insert_sql = """
                    INSERT OR REPLACE INTO tnt_plans (plan_name, plan_display_name, price_usd, monthly_limit, hourly_limit, vip_access)
                    VALUES (?, ?, ?, ?, ?, ?)
                """
            
            execute_sql_safe(cursor, insert_sql, (plan_name, display_name, price, monthly_limit, hourly_limit, vip_access), 
                           f"Adding plan: {display_name}")
        
        # Step 5: ایجاد ایندکس‌ها برای بهبود عملکرد
        print("\n🚀 Step 5: Creating performance indexes...")
        
        indexes = [
            ("idx_users_tnt_plan", "CREATE INDEX IF NOT EXISTS idx_users_tnt_plan ON users(tnt_plan_type, tnt_plan_end)"),
            ("idx_usage_tracking_user_date", "CREATE INDEX IF NOT EXISTS idx_usage_tracking_user_date ON tnt_usage_tracking(user_id, usage_date)"),
            ("idx_usage_tracking_user_hour", "CREATE INDEX IF NOT EXISTS idx_usage_tracking_user_hour ON tnt_usage_tracking(user_id, usage_date, usage_hour)"),
            ("idx_tnt_plans_active", "CREATE INDEX IF NOT EXISTS idx_tnt_plans_active ON tnt_plans(plan_name, is_active)")
        ]
        
        for index_name, sql in indexes:
            execute_sql_safe(cursor, sql, description=f"Creating {index_name}")
        
        # Step 6: به‌روزرسانی کاربران موجود برای سازگاری با سیستم قدیم
        print("\n🔄 Step 6: Updating existing users...")
        
        if db_type == "postgresql":
            # کاربران با اشتراک فعال قدیمی را به TNT_MINI تبدیل کن
            update_sql = """
                UPDATE users 
                SET tnt_plan_type = 'TNT_MINI',
                    tnt_monthly_limit = 60,
                    tnt_hourly_limit = 2,
                    tnt_plan_start = created_at,
                    tnt_plan_end = subscription_end
                WHERE is_active = true AND subscription_end > CURRENT_DATE
            """
        else:
            update_sql = """
                UPDATE users 
                SET tnt_plan_type = 'TNT_MINI',
                    tnt_monthly_limit = 60,
                    tnt_hourly_limit = 2,
                    tnt_plan_start = created_at,
                    tnt_plan_end = subscription_end
                WHERE is_active = 1 AND subscription_end > date('now')
            """
        
        execute_sql_safe(cursor, update_sql, description="Updating existing subscribers to TNT_MINI")
        
        # Final: Commit all changes
        print("\n💾 Committing all changes...")
        conn.commit()
        
        # Verification
        print("\n🔍 Final verification...")
        
        if db_type == "postgresql":
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name LIKE '%tnt%'
                ORDER BY table_name
            """)
        else:
            cursor.execute("""
                SELECT name 
                FROM sqlite_master 
                WHERE type='table' AND name LIKE '%tnt%'
                ORDER BY name
            """)
        
        tnt_tables = [row[0] for row in cursor.fetchall()]
        print(f"📊 TNT tables created: {', '.join(tnt_tables)}")
        
        # چک کردن تعداد پلن‌ها
        cursor.execute("SELECT COUNT(*) FROM tnt_plans WHERE is_active = true" if db_type == "postgresql" else "SELECT COUNT(*) FROM tnt_plans WHERE is_active = 1")
        plan_count = cursor.fetchone()[0]
        print(f"💎 Active TNT plans: {plan_count}")
        
        print("\n🎉 TNT Plans Migration completed successfully!")
        print("✅ Database is ready for TNT limit system!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("🔄 Rolling back changes...")
        try:
            conn.rollback()
            print("✅ Rollback successful")
        except:
            print("❌ Rollback failed")
        return False
        
    finally:
        conn.close()
        print("🔒 Database connection closed")

if __name__ == "__main__":
    print("🛠️ TNT Plans Migration Tool")
    print("Adding limit system and new subscription plans")
    print("=" * 60)
    
    success = tnt_plans_migration()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("🚀 Ready for TNT limit system!")
    else:
        print("\n❌ Migration failed!")
        print("📞 Check the error messages above")
    
    print("=" * 60)
