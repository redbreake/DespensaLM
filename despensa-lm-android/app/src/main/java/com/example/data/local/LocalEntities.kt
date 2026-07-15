package com.example.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "cached_products")
data class CachedProduct(
    @PrimaryKey val id: Int,
    val codigo_barras: String?,
    val nombre: String,
    val precio_costo: Double,
    val precio_venta: Double,
    val stock_actual: Int,
    val stock_minimo: Int,
    val activo_en_catalogo: Boolean,
    val imagen_url: String?
)

@Entity(tableName = "cached_clients")
data class CachedClient(
    @PrimaryKey val id: Int,
    val nombre: String,
    val telefono: String,
    val saldo_actual: Double
)

@Entity(tableName = "offline_sales")
data class OfflineSale(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val fecha: String,
    val monto_total: Double,
    val metodo_pago: String,
    val notas: String,
    val cliente_id: Int?,
    val items_json: String, // format: [{"producto_id": 14, "cantidad": 2, "precio_unitario": 4000.0}]
    val is_synced: Boolean = false
)
