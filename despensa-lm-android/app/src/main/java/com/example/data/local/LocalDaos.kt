package com.example.data.local

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface ProductDao {
    @Query("SELECT * FROM cached_products ORDER BY nombre ASC")
    fun getAllProducts(): Flow<List<CachedProduct>>

    @Query("SELECT * FROM cached_products WHERE nombre LIKE '%' || :query || '%' OR codigo_barras LIKE '%' || :query || '%' ORDER BY nombre ASC")
    fun searchProducts(query: String): Flow<List<CachedProduct>>

    @Query("SELECT * FROM cached_products WHERE codigo_barras = :barcode LIMIT 1")
    suspend fun getProductByBarcode(barcode: String): CachedProduct?

    @Query("SELECT * FROM cached_products WHERE id = :id LIMIT 1")
    suspend fun getProductById(id: Int): CachedProduct?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertProducts(products: List<CachedProduct>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertProduct(product: CachedProduct)

    @Update
    suspend fun updateProduct(product: CachedProduct)

    @Query("DELETE FROM cached_products")
    suspend fun clearAllProducts()

    @Query("DELETE FROM cached_products WHERE id = :id")
    suspend fun deleteProductById(id: Int)
}

@Dao
interface ClientDao {
    @Query("SELECT * FROM cached_clients ORDER BY nombre ASC")
    fun getAllClients(): Flow<List<CachedClient>>

    @Query("SELECT * FROM cached_clients WHERE nombre LIKE '%' || :query || '%' ORDER BY nombre ASC")
    fun searchClients(query: String): Flow<List<CachedClient>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertClients(clients: List<CachedClient>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertClient(client: CachedClient)

    @Query("DELETE FROM cached_clients")
    suspend fun clearAllClients()
}

@Dao
interface OfflineSaleDao {
    @Query("SELECT * FROM offline_sales WHERE is_synced = 0 ORDER BY id ASC")
    fun getUnsyncedSalesFlow(): Flow<List<OfflineSale>>

    @Query("SELECT * FROM offline_sales WHERE is_synced = 0 ORDER BY id ASC")
    suspend fun getUnsyncedSales(): List<OfflineSale>

    @Query("SELECT * FROM offline_sales ORDER BY id DESC")
    fun getAllOfflineSales(): Flow<List<OfflineSale>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertSale(sale: OfflineSale): Long

    @Update
    suspend fun updateSale(sale: OfflineSale)

    @Delete
    suspend fun deleteSale(sale: OfflineSale)

    @Query("DELETE FROM offline_sales WHERE is_synced = 1")
    suspend fun deleteSyncedSales()
}
