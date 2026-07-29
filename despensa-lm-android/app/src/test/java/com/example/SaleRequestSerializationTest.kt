package com.example

import com.example.data.remote.SaleItemRequest
import com.example.data.remote.SaleRequest
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class SaleRequestSerializationTest {
    private val adapter = Moshi.Builder()
        .add(KotlinJsonAdapterFactory())
        .build()
        .adapter(SaleRequest::class.java)

    @Test
    fun preservesOperationIdAndUnitPrice() {
        val request = SaleRequest(
            operacionId = "8db86085-ae6d-4436-a035-56395ac68981",
            fecha = "2026-07-20",
            montoTotal = 3000.0,
            metodoPago = "EFECTIVO",
            notas = "Venta",
            clienteId = null,
            items = listOf(
                SaleItemRequest(
                    productoId = 12,
                    cantidad = 2,
                    precioUnitario = 1500.0
                )
            )
        )

        val json = adapter.toJson(request)
        val decoded = adapter.fromJson(json)!!

        assertTrue(json.contains("\"operacion_id\""))
        assertTrue(json.contains("\"precio_unitario\""))
        assertEquals(request.operacionId, decoded.operacionId)
        assertEquals(request.items.single().precioUnitario, decoded.items.single().precioUnitario)
    }

    @Test
    fun acceptsLegacyItemsWithoutUnitPrice() {
        val json = """
            {
              "operacion_id": "00000000-0000-0000-0000-000000000001",
              "fecha": "2026-07-20",
              "monto_total": 3000.0,
              "metodo_pago": "EFECTIVO",
              "notas": "",
              "cliente_id": null,
              "items": [{"producto_id": 12, "cantidad": 2}]
            }
        """.trimIndent()

        val decoded = adapter.fromJson(json)!!

        assertNull(decoded.items.single().precioUnitario)
    }
}
