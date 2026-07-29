package com.example.data.remote

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass
import retrofit2.Response
import retrofit2.http.*

@JsonClass(generateAdapter = true)
data class LoginRequest(
    val username: String,
    val password: String
)

@JsonClass(generateAdapter = true)
data class UserInfo(
    val username: String,
    val email: String?
)

@JsonClass(generateAdapter = true)
data class LoginResponse(
    val success: Boolean,
    val user: UserInfo?,
    val error: String?
)

@JsonClass(generateAdapter = true)
data class ProductResponse(
    val id: Int,
    @Json(name = "codigo_barras") val codigoBarras: String?,
    val nombre: String,
    @Json(name = "precio_costo") val precioCosto: Double,
    @Json(name = "precio_venta") val precioVenta: Double,
    @Json(name = "stock_actual") val stockActual: Int,
    @Json(name = "stock_minimo") val stockMinimo: Int,
    @Json(name = "activo_en_catalogo") val activoEnCatalogo: Boolean,
    @Json(name = "imagen_url") val imagenUrl: String?
)

@JsonClass(generateAdapter = true)
data class ClientResponse(
    val id: Int,
    val nombre: String,
    val telefono: String?,
    val notas: String? = null,
    @Json(name = "saldo_actual") val saldoActual: Double?
)

@JsonClass(generateAdapter = true)
data class ClientRequest(
    val nombre: String,
    val telefono: String,
    val notas: String
)

@JsonClass(generateAdapter = true)
data class AccountMovementResponse(
    val id: Int,
    val fecha: String,
    @Json(name = "tipo_movimiento") val tipoMovimiento: String,
    val monto: Double,
    val descripcion: String
)

@JsonClass(generateAdapter = true)
data class ClientDetailResponse(
    val cliente: ClientResponse,
    val movimientos: List<AccountMovementResponse>
)

@JsonClass(generateAdapter = true)
data class AccountMovementRequest(
    @Json(name = "tipo_movimiento") val tipoMovimiento: String,
    val monto: Double,
    val descripcion: String
)

@JsonClass(generateAdapter = true)
data class AccountMovementCreatedResponse(
    val id: Int,
    @Json(name = "saldo_actual") val saldoActual: Double
)

@JsonClass(generateAdapter = true)
data class BasicSuccessResponse(val success: Boolean)

@JsonClass(generateAdapter = true)
data class SaleItemRequest(
    @Json(name = "producto_id") val productoId: Int,
    val cantidad: Int,
    @Json(name = "precio_unitario") val precioUnitario: Double? = null
)

@JsonClass(generateAdapter = true)
data class SaleRequest(
    @Json(name = "operacion_id") val operacionId: String,
    val fecha: String,
    @Json(name = "monto_total") val montoTotal: Double,
    @Json(name = "metodo_pago") val metodoPago: String,
    val notas: String,
    @Json(name = "cliente_id") val clienteId: Int?,
    val items: List<SaleItemRequest>
)

@JsonClass(generateAdapter = true)
data class SaleResponse(
    val success: Boolean,
    @Json(name = "venta_id") val ventaId: Int?,
    @Json(name = "operacion_id") val operacionId: String? = null,
    @Json(name = "monto_total") val montoTotal: Double?,
    @Json(name = "nuevo_saldo_cliente") val nuevoSaldoCliente: Double?,
    val duplicada: Boolean = false,
    val error: String?
)

interface ApiService {

    @POST("api/login/")
    suspend fun login(@Body request: LoginRequest): Response<LoginResponse>

    @GET("api/productos/buscar/")
    suspend fun buscarProductoPorCodigo(
        @Query("codigo_barras") codigoBarras: String
    ): Response<ProductResponse>

    @GET("api/productos/")
    suspend fun buscarProductos(
        @Query("q") query: String
    ): Response<List<ProductResponse>>

    @POST("api/productos/guardar/")
    suspend fun crearProducto(
        @Body producto: ProductResponse
    ): Response<ProductResponse>

    @PUT("api/productos/{id}/editar/")
    suspend fun editarProducto(
        @Path("id") id: Int,
        @Body producto: ProductResponse
    ): Response<ProductResponse>

    @DELETE("api/productos/{id}/eliminar/")
    suspend fun eliminarProducto(@Path("id") id: Int): Response<BasicSuccessResponse>

    @GET("api/clientes/")
    suspend fun listarClientes(): Response<List<ClientResponse>>

    @POST("api/clientes/guardar/")
    suspend fun crearCliente(@Body cliente: ClientRequest): Response<ClientResponse>

    @PUT("api/clientes/{id}/editar/")
    suspend fun editarCliente(@Path("id") id: Int, @Body cliente: ClientRequest): Response<ClientResponse>

    @GET("api/clientes/{id}/movimientos/")
    suspend fun detalleCliente(@Path("id") id: Int): Response<ClientDetailResponse>

    @POST("api/clientes/{id}/movimientos/")
    suspend fun registrarMovimiento(
        @Path("id") id: Int,
        @Body movimiento: AccountMovementRequest
    ): Response<AccountMovementCreatedResponse>

    @POST("api/ventas/")
    suspend fun registrarVenta(
        @Body request: SaleRequest
    ): Response<SaleResponse>
}
