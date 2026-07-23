package com.example.data.local

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

@Database(
    entities = [CachedProduct::class, CachedClient::class, OfflineSale::class],
    version = 2,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun productDao(): ProductDao
    abstract fun clientDao(): ClientDao
    abstract fun offlineSaleDao(): OfflineSaleDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun getDatabase(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "despensa_lm_database"
                )
                .addMigrations(MIGRATION_1_2)
                .build()
                INSTANCE = instance
                instance
            }
        }

        private val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL(
                    "ALTER TABLE offline_sales " +
                        "ADD COLUMN operation_id TEXT NOT NULL DEFAULT ''"
                )
                db.execSQL(
                    "UPDATE offline_sales " +
                        "SET operation_id = printf(" +
                        "'00000000-0000-0000-0000-%012d', id" +
                        ") " +
                        "WHERE operation_id = ''"
                )
                db.execSQL(
                    "CREATE UNIQUE INDEX IF NOT EXISTS " +
                        "index_offline_sales_operation_id " +
                        "ON offline_sales(operation_id)"
                )
            }
        }
    }
}
