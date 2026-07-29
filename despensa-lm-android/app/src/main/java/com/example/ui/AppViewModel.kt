package com.example.ui

import android.app.Application
import android.content.Context
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.DespensaLMApplication
import com.example.data.local.CachedClient
import com.example.data.local.CachedProduct
import com.example.data.local.OfflineSale
import com.example.data.remote.LoginRequest
import com.example.data.remote.AccountMovementRequest
import com.example.data.remote.ClientDetailResponse
import com.example.data.remote.ClientRequest
import com.example.data.remote.ProductResponse
import com.example.data.remote.SaleItemRequest
import com.example.data.repository.ClientRepository
import com.example.data.repository.ProductRepository
import com.example.data.repository.SalesRepository
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

class AppViewModel(
    application: Application,
    private val productRepository: ProductRepository,
    private val clientRepository: ClientRepository,
    private val salesRepository: SalesRepository
) : AndroidViewModel(application) {

    private val app = application as DespensaLMApplication
    private val loginPrefs = app.getSharedPreferences("despensa_lm_auth", Context.MODE_PRIVATE)
    private val uiPrefs = app.getSharedPreferences("despensa_lm_ui", Context.MODE_PRIVATE)

    var darkThemeOverride by mutableStateOf<Boolean?>(
        if (uiPrefs.contains("dark_theme")) uiPrefs.getBoolean("dark_theme", false) else null
    )
        private set

    fun toggleTheme(currentDarkTheme: Boolean) {
        val newValue = !currentDarkTheme
        uiPrefs.edit().putBoolean("dark_theme", newValue).apply()
        darkThemeOverride = newValue
    }

    // --- Dynamic Base URL ---
    var baseUrlState by mutableStateOf(app.networkService.getSavedBaseUrl())
        private set

    fun updateBaseUrl(url: String) {
        app.networkService.saveBaseUrl(url)
        baseUrlState = app.networkService.getSavedBaseUrl()
    }

    // --- Authentication ---
    var isLoggedIn by mutableStateOf(loginPrefs.getBoolean("is_logged_in", false))
        private set

    var loggedInUsername by mutableStateOf(loginPrefs.getString("username", "") ?: "")
        private set

    var loggedInEmail by mutableStateOf(loginPrefs.getString("email", "") ?: "")
        private set

    var loginLoading by mutableStateOf(false)
    var loginError by mutableStateOf<String?>(null)

    fun login(username: String, pword: String, onSuccess: () -> Unit = {}) {
        viewModelScope.launch {
            loginLoading = true
            loginError = null
            try {
                val api = app.networkService.getApi()
                if (api == null) {
                    loginError = "URL de servidor inválida o inaccesible."
                    loginLoading = false
                    return@launch
                }
                val response = api.login(LoginRequest(username, pword))
                if (response.isSuccessful && response.body() != null) {
                    val body = response.body()!!
                    if (body.success) {
                        loginPrefs.edit().apply {
                            putBoolean("is_logged_in", true)
                            putString("username", body.user?.username ?: username)
                            putString("email", body.user?.email ?: "")
                        }.apply()

                        isLoggedIn = true
                        loggedInUsername = body.user?.username ?: username
                        loggedInEmail = body.user?.email ?: ""
                        
                        // Sync catalog right after login
                        syncCatalog()
                        onSuccess()
                    } else {
                        loginError = body.error ?: "Credenciales de login inválidas."
                    }
                } else {
                    loginError = "Error en el servidor: Código ${response.code()}"
                }
            } catch (e: Exception) {
                e.printStackTrace()
                loginError = "Error de red: ${e.localizedMessage ?: "No se pudo conectar"}"
            } finally {
                loginLoading = false
            }
        }
    }

    fun logout() {
        loginPrefs.edit().clear().apply()
        app.networkService.cookieJar.clearCookies()
        isLoggedIn = false
        loggedInUsername = ""
        loggedInEmail = ""
    }

    // --- Inventory & Sync ---
    val allProducts: StateFlow<List<CachedProduct>> = productRepository.allCachedProducts
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val allClients: StateFlow<List<CachedClient>> = clientRepository.allCachedClients
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val unsyncedSales: StateFlow<List<OfflineSale>> = salesRepository.unsyncedSales
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val allOfflineSales: StateFlow<List<OfflineSale>> = salesRepository.allOfflineSales
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    var isSyncingCatalog by mutableStateOf(false)
    var catalogSyncMessage by mutableStateOf<String?>(null)

    init {
        if (isLoggedIn) {
            syncCatalog()
        }
    }

    fun syncCatalog() {
        viewModelScope.launch {
            isSyncingCatalog = true
            catalogSyncMessage = "Sincronizando productos..."
            val prodOk = productRepository.syncProducts()
            catalogSyncMessage = "Sincronizando clientes..."
            val clientOk = clientRepository.syncClients()
            
            // Sync any pending local sales
            catalogSyncMessage = "Subiendo ventas pendientes..."
            val salesSyncedCount = salesRepository.syncPendingSales()

            catalogSyncMessage = if (prodOk && clientOk) {
                if (salesSyncedCount > 0) {
                    "Sincronización exitosa. $salesSyncedCount ventas subidas."
                } else {
                    "Catálogo actualizado correctamente."
                }
            } else {
                "Sincronización parcial (offline). $salesSyncedCount ventas subidas."
            }
            isSyncingCatalog = false
        }
    }

    // --- Quick Sale Shopping Cart ---
    val cart = mutableStateMapOf<CachedProduct, Int>()

    val cartSubtotal: Double
        get() = cart.entries.sumOf { it.key.precio_venta * it.value }

    fun addProductToCart(product: CachedProduct, quantity: Int = 1) {
        // Enforce stock warning constraint but allow sale
        val currentQty = cart[product] ?: 0
        cart[product] = currentQty + quantity
    }

    fun removeProductFromCart(product: CachedProduct) {
        cart.remove(product)
    }

    fun updateProductCartQty(product: CachedProduct, qty: Int) {
        if (qty <= 0) {
            cart.remove(product)
        } else {
            cart[product] = qty
        }
    }

    fun clearCart() {
        cart.clear()
        selectedClient = null
        saleNotes = ""
    }

    // Sell Fields
    var selectedPaymentMethod by mutableStateOf("EFECTIVO")
    var selectedClient by mutableStateOf<CachedClient?>(null)
    var saleNotes by mutableStateOf("")
    var saleLoading by mutableStateOf(false)
    var saleStatusMessage by mutableStateOf<String?>(null)

    fun submitVenta(onSuccess: () -> Unit = {}) {
        if (cart.isEmpty()) {
            saleStatusMessage = "El carrito de ventas está vacío"
            return
        }

        if (selectedPaymentMethod == "FIADO" && selectedClient == null) {
            saleStatusMessage = "Venta 'Fiado' requiere asociar un Cliente."
            return
        }

        viewModelScope.launch {
            saleLoading = true
            saleStatusMessage = "Procesando venta..."

            val sdf = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
            val currentDate = sdf.format(Date())

            val itemsRequest = cart.map {
                SaleItemRequest(
                    productoId = it.key.id,
                    cantidad = it.value,
                    precioUnitario = it.key.precio_venta
                )
            }

            val result = salesRepository.registerSale(
                fecha = currentDate,
                montoTotal = cartSubtotal,
                metodoPago = selectedPaymentMethod,
                notas = saleNotes,
                clienteId = selectedClient?.id,
                items = itemsRequest
            )

            saleStatusMessage = result.second
            if (result.first) {
                clearCart()
                // Sync to refresh updated local status
                syncCatalog()
                onSuccess()
            }
            saleLoading = false
        }
    }

    // --- Barcode Scanning Flows ---
    var lastScannedBarcode by mutableStateOf("")
    var isNewProductScannedDialogShowing by mutableStateOf(false)
    var scannedNotFoundBarcode by mutableStateOf("")

    fun onBarcodeScanned(barcode: String) {
        lastScannedBarcode = barcode

        viewModelScope.launch {
            saleStatusMessage = "Buscando código de barras: $barcode"
            val matchedProduct = productRepository.buscarYGuardarProductoPorCodigo(barcode)
            if (matchedProduct != null) {
                addProductToCart(matchedProduct, 1)
                saleStatusMessage = "Agregado: ${matchedProduct.nombre}"
            } else {
                // Not found on remote/local cache
                scannedNotFoundBarcode = barcode
                isNewProductScannedDialogShowing = true
                saleStatusMessage = "Código de barras no encontrado."
            }
        }
    }

    // --- Inventory Create / Edit Forms ---
    var productFormBarcode by mutableStateOf("")
    var productFormNombre by mutableStateOf("")
    var productFormCosto by mutableStateOf("")
    var productFormVenta by mutableStateOf("")
    var productFormStockActual by mutableStateOf("")
    var productFormStockMinimo by mutableStateOf("5")
    var productFormActivo by mutableStateOf(true)

    var isEditingMode by mutableStateOf(false)
    var selectedProductIdToEdit by mutableStateOf<Int?>(null)
    var selectedProductToEdit by mutableStateOf<CachedProduct?>(null)
        private set

    var saveProductLoading by mutableStateOf(false)
    var saveProductError by mutableStateOf<String?>(null)
    var deleteProductLoading by mutableStateOf(false)
    var deleteProductError by mutableStateOf<String?>(null)

    fun resetProductForm(existing: CachedProduct? = null, initialBarcode: String = "") {
        if (existing != null) {
            isEditingMode = true
            selectedProductIdToEdit = existing.id
            selectedProductToEdit = existing
            productFormBarcode = existing.codigo_barras ?: ""
            productFormNombre = existing.nombre
            productFormCosto = existing.precio_costo.toString()
            productFormVenta = existing.precio_venta.toString()
            productFormStockActual = existing.stock_actual.toString()
            productFormStockMinimo = existing.stock_minimo.toString()
            productFormActivo = existing.activo_en_catalogo
        } else {
            isEditingMode = false
            selectedProductIdToEdit = null
            selectedProductToEdit = null
            productFormBarcode = initialBarcode
            productFormNombre = ""
            productFormCosto = ""
            productFormVenta = ""
            productFormStockActual = ""
            productFormStockMinimo = "5"
            productFormActivo = true
        }
        saveProductError = null
        deleteProductError = null
    }

    fun submitProductForm(onComplete: () -> Unit) {
        if (productFormNombre.isBlank()) {
            saveProductError = "El nombre del producto no puede estar vacío"
            return
        }
        val costo = productFormCosto.toDoubleOrNull() ?: 0.0
        val venta = productFormVenta.toDoubleOrNull() ?: 0.0
        val stock = productFormStockActual.toIntOrNull() ?: 0
        val minStock = productFormStockMinimo.toIntOrNull() ?: 5

        if (costo <= 0 || venta <= 0) {
            saveProductError = "Fije montos de precio válidos"
            return
        }

        viewModelScope.launch {
            saveProductLoading = true
            saveProductError = null

            val pResponse = ProductResponse(
                id = selectedProductIdToEdit ?: 0,
                codigoBarras = productFormBarcode.ifBlank { null },
                nombre = productFormNombre,
                precioCosto = costo,
                precioVenta = venta,
                stockActual = stock,
                stockMinimo = minStock,
                activoEnCatalogo = productFormActivo,
                imagenUrl = null
            )

            val result = if (isEditingMode && selectedProductIdToEdit != null) {
                productRepository.editProduct(selectedProductIdToEdit!!, pResponse)
            } else {
                productRepository.createProduct(pResponse)
            }

            if (result.isSuccess) {
                syncCatalog()
                onComplete()
            } else {
                saveProductError = result.exceptionOrNull()?.message ?: "Error al guardar el producto en el servidor."
            }
            saveProductLoading = false
        }
    }

    fun deleteProduct(product: CachedProduct, onComplete: () -> Unit) {
        viewModelScope.launch {
            deleteProductLoading = true
            deleteProductError = null
            val result = productRepository.deleteProduct(product.id)
            if (result.isSuccess) {
                cart.remove(product)
                onComplete()
            } else {
                deleteProductError = result.exceptionOrNull()?.message ?: "No se pudo eliminar el producto."
            }
            deleteProductLoading = false
        }
    }

    // --- Client management ---
    var clientDetail by mutableStateOf<ClientDetailResponse?>(null)
        private set
    var clientActionLoading by mutableStateOf(false)
        private set
    var clientActionError by mutableStateOf<String?>(null)
        private set

    fun clearClientActionState() {
        clientDetail = null
        clientActionError = null
    }

    fun loadClientDetail(clientId: Int) {
        viewModelScope.launch {
            clientActionLoading = true
            clientActionError = null
            val result = clientRepository.getClientDetail(clientId)
            clientDetail = result.getOrNull()
            if (result.isFailure) {
                clientActionError = result.exceptionOrNull()?.message ?: "No se pudo cargar la cuenta."
            }
            clientActionLoading = false
        }
    }

    fun saveClient(
        id: Int?,
        name: String,
        phone: String,
        notes: String,
        onComplete: () -> Unit
    ) {
        if (name.isBlank()) {
            clientActionError = "El nombre es obligatorio."
            return
        }
        viewModelScope.launch {
            clientActionLoading = true
            clientActionError = null
            val result = clientRepository.saveClient(id, ClientRequest(name.trim(), phone.trim(), notes.trim()))
            if (result.isSuccess) {
                clientRepository.syncClients()
                onComplete()
            } else {
                clientActionError = result.exceptionOrNull()?.message ?: "No se pudo guardar el cliente."
            }
            clientActionLoading = false
        }
    }

    fun addClientMovement(
        clientId: Int,
        type: String,
        amount: String,
        description: String,
        onComplete: () -> Unit
    ) {
        val parsedAmount = amount.replace(',', '.').toDoubleOrNull()
        if (parsedAmount == null || parsedAmount <= 0) {
            clientActionError = "Ingresá un monto válido mayor que cero."
            return
        }
        viewModelScope.launch {
            clientActionLoading = true
            clientActionError = null
            val result = clientRepository.addMovement(
                clientId,
                AccountMovementRequest(type, parsedAmount, description.trim())
            )
            if (result.isSuccess) {
                clientRepository.syncClients()
                clientDetail = clientRepository.getClientDetail(clientId).getOrNull()
                onComplete()
            } else {
                clientActionError = result.exceptionOrNull()?.message ?: "No se pudo registrar el movimiento."
            }
            clientActionLoading = false
        }
    }
}

class AppViewModelFactory(
    private val application: Application,
    private val productRepository: ProductRepository,
    private val clientRepository: ClientRepository,
    private val salesRepository: SalesRepository
) : ViewModelProvider.Factory {
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(AppViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return AppViewModel(application, productRepository, clientRepository, salesRepository) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class")
    }
}
