package com.example.data.repository

import com.example.data.local.*
import com.example.data.remote.*
import com.squareup.moshi.Moshi
import com.squareup.moshi.Types
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext
import java.util.UUID

class ProductRepository(
    private val productDao: ProductDao,
    private val networkService: NetworkService
) {
    val allCachedProducts: Flow<List<CachedProduct>> = productDao.getAllProducts()

    fun searchCachedProducts(query: String): Flow<List<CachedProduct>> {
        return productDao.searchProducts(query)
    }

    suspend fun syncProducts(): Boolean = withContext(Dispatchers.IO) {
        val api = networkService.getApi() ?: return@withContext false
        try {
            val response = api.buscarProductos("")
            if (response.isSuccessful && response.body() != null) {
                val remoteList = response.body()!!
                val cached = remoteList.map {
                    CachedProduct(
                        id = it.id,
                        codigo_barras = it.codigoBarras,
                        nombre = it.nombre,
                        precio_costo = it.precioCosto,
                        precio_venta = it.precioVenta,
                        stock_actual = it.stockActual,
                        stock_minimo = it.stockMinimo,
                        activo_en_catalogo = it.activoEnCatalogo,
                        imagen_url = it.imagenUrl
                    )
                }
                productDao.clearAllProducts()
                productDao.insertProducts(cached)
                return@withContext true
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
        return@withContext false
    }

    suspend fun buscarYGuardarProductoPorCodigo(barcode: String): CachedProduct? = withContext(Dispatchers.IO) {
        // 1. Try remote API first
        val api = networkService.getApi()
        if (api != null) {
            try {
                val response = api.buscarProductoPorCodigo(barcode)
                if (response.isSuccessful && response.body() != null) {
                    val r = response.body()!!
                    val cached = CachedProduct(
                        id = r.id,
                        codigo_barras = r.codigoBarras,
                        nombre = r.nombre,
                        precio_costo = r.precioCosto,
                        precio_venta = r.precioVenta,
                        stock_actual = r.stockActual,
                        stock_minimo = r.stockMinimo,
                        activo_en_catalogo = r.activoEnCatalogo,
                        imagen_url = r.imagenUrl
                    )
                    productDao.insertProduct(cached)
                    return@withContext cached
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
        // 2. Fallback to local DB
        return@withContext productDao.getProductByBarcode(barcode)
    }

    suspend fun createProduct(p: ProductResponse): Result<CachedProduct> = withContext(Dispatchers.IO) {
        val api = networkService.getApi() ?: return@withContext Result.failure(Exception("Servidor remoto no inicializado o sin conexión."))
        try {
             val response = api.crearProducto(p)
             if (response.isSuccessful && response.body() != null) {
                 val r = response.body()!!
                 val cached = CachedProduct(
                     id = r.id,
                     codigo_barras = r.codigoBarras,
                     nombre = r.nombre,
                     precio_costo = r.precioCosto,
                     precio_venta = r.precioVenta,
                     stock_actual = r.stockActual,
                     stock_minimo = r.stockMinimo,
                     activo_en_catalogo = r.activoEnCatalogo,
                     imagen_url = r.imagenUrl
                 )
                 productDao.insertProduct(cached)
                 return@withContext Result.success(cached)
             } else {
                val code = response.code()
                val rawError = response.errorBody()?.string()
                val friendlyError = parseRemoteError(code, rawError)
                return@withContext Result.failure(Exception(friendlyError))
            }
        } catch (e: Exception) {
            e.printStackTrace()
            return@withContext Result.failure(e)
        }
    }

    suspend fun editProduct(id: Int, p: ProductResponse): Result<CachedProduct> = withContext(Dispatchers.IO) {
        val api = networkService.getApi() ?: return@withContext Result.failure(Exception("Servidor remoto no inicializado o sin conexión."))
        try {
            val response = api.editarProducto(id, p)
            if (response.isSuccessful && response.body() != null) {
                val r = response.body()!!
                val cached = CachedProduct(
                    id = r.id,
                    codigo_barras = r.codigoBarras,
                    nombre = r.nombre,
                    precio_costo = r.precioCosto,
                    precio_venta = r.precioVenta,
                    stock_actual = r.stockActual,
                    stock_minimo = r.stockMinimo,
                    activo_en_catalogo = r.activoEnCatalogo,
                    imagen_url = r.imagenUrl
                )
                productDao.insertProduct(cached)
                return@withContext Result.success(cached)
            } else {
                val code = response.code()
                val rawError = response.errorBody()?.string()
                val friendlyError = parseRemoteError(code, rawError)
                return@withContext Result.failure(Exception(friendlyError))
            }
        } catch (e: Exception) {
            e.printStackTrace()
            return@withContext Result.failure(e)
        }
    }

    suspend fun deleteProduct(id: Int): Result<Unit> = withContext(Dispatchers.IO) {
        val api = networkService.getApi()
            ?: return@withContext Result.failure(Exception("Servidor remoto no inicializado o sin conexión."))
        try {
            val response = api.eliminarProducto(id)
            if (response.isSuccessful && response.body()?.success == true) {
                productDao.deleteProductById(id)
                Result.success(Unit)
            } else {
                Result.failure(Exception(parseRemoteError(response.code(), response.errorBody()?.string())))
            }
        } catch (e: Exception) {
            e.printStackTrace()
            Result.failure(e)
        }
    }

    private fun parseRemoteError(code: Int, errorBody: String?): String {
        if (errorBody.isNullOrBlank()) return "Error del servidor (código $code)"
        if (errorBody.trimStart().startsWith("<")) {
            return "Esta función todavía no está disponible en el servidor."
        }
        return try {
            val clean = errorBody.replace(Regex("[{}\"\\[\\]]"), "")
                .replace(":", ": ")
                .trim()
            if (clean.length > 200) clean.take(200) + "..." else clean
        } catch (e: Exception) {
            errorBody.take(150)
        }
    }
}

class ClientRepository(
    private val clientDao: ClientDao,
    private val networkService: NetworkService
) {
    val allCachedClients: Flow<List<CachedClient>> = clientDao.getAllClients()

    fun searchClients(query: String): Flow<List<CachedClient>> {
        return clientDao.searchClients(query)
    }

    suspend fun syncClients(): Boolean = withContext(Dispatchers.IO) {
        val api = networkService.getApi() ?: return@withContext false
        try {
            val response = api.listarClientes()
            if (response.isSuccessful && response.body() != null) {
                val remoteList = response.body()!!
                val cached = remoteList.map {
                    CachedClient(
                        id = it.id,
                        nombre = it.nombre,
                        telefono = it.telefono ?: "",
                        saldo_actual = it.saldoActual ?: 0.0
                    )
                }
                clientDao.clearAllClients()
                clientDao.insertClients(cached)
                return@withContext true
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
        return@withContext false
    }

    suspend fun saveClient(id: Int?, request: ClientRequest): Result<CachedClient> = withContext(Dispatchers.IO) {
        val api = networkService.getApi()
            ?: return@withContext Result.failure(Exception("Servidor remoto no inicializado o sin conexión."))
        try {
            val response = if (id == null) api.crearCliente(request) else api.editarCliente(id, request)
            val body = response.body()
            if (response.isSuccessful && body != null) {
                val cached = body.toCachedClient()
                clientDao.insertClient(cached)
                Result.success(cached)
            } else {
                Result.failure(Exception(apiError(response.code(), response.errorBody()?.string())))
            }
        } catch (e: Exception) {
            e.printStackTrace()
            Result.failure(e)
        }
    }

    suspend fun getClientDetail(id: Int): Result<ClientDetailResponse> = withContext(Dispatchers.IO) {
        val api = networkService.getApi()
            ?: return@withContext Result.failure(Exception("Servidor remoto no inicializado o sin conexión."))
        try {
            val response = api.detalleCliente(id)
            val body = response.body()
            if (response.isSuccessful && body != null) {
                clientDao.insertClient(body.cliente.toCachedClient())
                Result.success(body)
            } else {
                Result.failure(Exception(apiError(response.code(), response.errorBody()?.string())))
            }
        } catch (e: Exception) {
            e.printStackTrace()
            Result.failure(e)
        }
    }

    suspend fun addMovement(id: Int, request: AccountMovementRequest): Result<Double> = withContext(Dispatchers.IO) {
        val api = networkService.getApi()
            ?: return@withContext Result.failure(Exception("Servidor remoto no inicializado o sin conexión."))
        try {
            val response = api.registrarMovimiento(id, request)
            val body = response.body()
            if (response.isSuccessful && body != null) {
                Result.success(body.saldoActual)
            } else {
                Result.failure(Exception(apiError(response.code(), response.errorBody()?.string())))
            }
        } catch (e: Exception) {
            e.printStackTrace()
            Result.failure(e)
        }
    }

    private fun ClientResponse.toCachedClient() = CachedClient(
        id = id,
        nombre = nombre,
        telefono = telefono.orEmpty(),
        saldo_actual = saldoActual ?: 0.0
    )

    private fun apiError(code: Int, body: String?): String {
        if (body.isNullOrBlank()) return "Error del servidor (código $code)"
        if (body.trimStart().startsWith("<")) {
            return "Esta función todavía no está disponible en el servidor."
        }
        return body.replace(Regex("[{}\"\\[\\]]"), "")
            .replace(":", ": ")
            .trim()
            .take(200)
    }
}

class SalesRepository(
    private val offlineSaleDao: OfflineSaleDao,
    private val productDao: ProductDao,
    private val networkService: NetworkService
) {
    val unsyncedSales: Flow<List<OfflineSale>> = offlineSaleDao.getUnsyncedSalesFlow()
    val allOfflineSales: Flow<List<OfflineSale>> = offlineSaleDao.getAllOfflineSales()

    private val moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()
    private val listType = Types.newParameterizedType(List::class.java, SaleItemRequest::class.java)
    private val itemsAdapter = moshi.adapter<List<SaleItemRequest>>(listType)

    suspend fun registerSale(
        fecha: String,
        montoTotal: Double,
        metodoPago: String,
        notas: String,
        clienteId: Int?,
        items: List<SaleItemRequest>
    ): Pair<Boolean, String> = withContext(Dispatchers.IO) {
        val api = networkService.getApi()
        val itemsJson = itemsAdapter.toJson(items)
        val operationId = UUID.randomUUID().toString()

        if (api != null) {
            try {
                val request = SaleRequest(
                    operacionId = operationId,
                    fecha = fecha,
                    montoTotal = montoTotal,
                    metodoPago = metodoPago,
                    notas = notas,
                    clienteId = clienteId,
                    items = items
                )
                val response = api.registrarVenta(request)
                if (response.isSuccessful && response.body() != null) {
                    val body = response.body()!!
                    if (body.success) {
                        // Success! Update local stock for these products locally just in case
                        decrementLocalStock(items)
                        // Add to local sales as synced
                        offlineSaleDao.insertSale(
                            OfflineSale(
                                fecha = fecha,
                                operation_id = operationId,
                                monto_total = montoTotal,
                                metodo_pago = metodoPago,
                                notas = notas,
                                cliente_id = clienteId,
                                items_json = itemsJson,
                                is_synced = true
                            )
                        )
                        return@withContext Pair(true, "Venta registrada exitosamente en el servidor.")
                    } else {
                        return@withContext Pair(false, "Error: ${body.error ?: "desconocido"}")
                    }
                } else if (!response.isSuccessful) {
                    return@withContext Pair(
                        false,
                        apiError(response.code(), response.errorBody()?.string())
                    )
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }

        // Offline Fallback
        decrementLocalStock(items)
        offlineSaleDao.insertSale(
            OfflineSale(
                fecha = fecha,
                operation_id = operationId,
                monto_total = montoTotal,
                metodo_pago = metodoPago,
                notas = notas,
                cliente_id = clienteId,
                items_json = itemsJson,
                is_synced = false
            )
        )
        return@withContext Pair(true, "Sin conexión. Venta guardada localmente para sincronizar luego.")
    }

    private suspend fun decrementLocalStock(items: List<SaleItemRequest>) {
        for (item in items) {
            val prod = productDao.getProductById(item.productoId)
            if (prod != null) {
                val updatedStock = (prod.stock_actual - item.cantidad).coerceAtLeast(0)
                productDao.updateProduct(prod.copy(stock_actual = updatedStock))
            }
        }
    }

    suspend fun syncPendingSales(): Int = withContext(Dispatchers.IO) {
        val pending = offlineSaleDao.getUnsyncedSales()
        if (pending.isEmpty()) return@withContext 0
        val api = networkService.getApi() ?: return@withContext 0

        var successCount = 0
        for (sale in pending) {
            try {
                val itemsList: List<SaleItemRequest>? = itemsAdapter.fromJson(sale.items_json)
                if (itemsList != null) {
                    val request = SaleRequest(
                        operacionId = sale.operation_id,
                        fecha = sale.fecha,
                        montoTotal = sale.monto_total,
                        metodoPago = sale.metodo_pago,
                        notas = sale.notas,
                        clienteId = sale.cliente_id,
                        items = itemsList
                    )
                    val response = api.registrarVenta(request)
                    if (response.isSuccessful && response.body()?.success == true) {
                        offlineSaleDao.updateSale(sale.copy(is_synced = true))
                        successCount++
                    }
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
        return@withContext successCount
    }

    private fun apiError(code: Int, body: String?): String {
        if (body.isNullOrBlank()) return "Error del servidor (código $code)"
        if (body.trimStart().startsWith("<")) {
            return "El servidor devolvió una respuesta inesperada."
        }
        return body.replace(Regex("[{}\"\\[\\]]"), "")
            .replace(":", ": ")
            .trim()
            .take(200)
    }
}
