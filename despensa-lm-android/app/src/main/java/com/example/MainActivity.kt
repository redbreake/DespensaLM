package com.example

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.ui.AppViewModel
import com.example.ui.AppViewModelFactory
import com.example.ui.screens.ClientListScreen
import com.example.ui.screens.InventoryScreen
import com.example.ui.screens.LoginScreen
import com.example.ui.screens.SaleScreen
import com.example.ui.theme.MyApplicationTheme

class MainActivity : ComponentActivity() {
    private val viewModel: AppViewModel by viewModels {
        val app = application as DespensaLMApplication
        AppViewModelFactory(app, app.productRepository, app.clientRepository, app.salesRepository)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            val isDarkTheme = viewModel.darkThemeOverride ?: isSystemInDarkTheme()
            MyApplicationTheme(darkTheme = isDarkTheme) {
                if (viewModel.isLoggedIn) AppMainDashboard(viewModel, isDarkTheme) else LoginScreen(viewModel)
            }
        }
    }
}

private data class MainDestination(val label: String, val icon: androidx.compose.ui.graphics.vector.ImageVector)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppMainDashboard(viewModel: AppViewModel, isDarkTheme: Boolean) {
    var activeTab by rememberSaveable { mutableIntStateOf(0) }
    var productFormRequest by rememberSaveable { mutableIntStateOf(0) }
    val unsyncedSales by viewModel.unsyncedSales.collectAsState()
    val destinations = remember {
        listOf(
            MainDestination("Caja", Icons.Default.ShoppingCart),
            MainDestination("Inventario", Icons.Default.List),
            MainDestination("Clientes", Icons.Default.Person)
        )
    }

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Despensa LM", style = MaterialTheme.typography.titleLarge)
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Surface(
                                modifier = Modifier.size(6.dp),
                                shape = androidx.compose.foundation.shape.CircleShape,
                                color = if (viewModel.isSyncingCatalog) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.primary
                            ) {}
                            Spacer(Modifier.width(6.dp))
                            Text(
                                if (viewModel.isSyncingCatalog) "Sincronizando datos" else "${viewModel.loggedInUsername} · ${if (unsyncedSales.isEmpty()) "Todo al día" else "${unsyncedSales.size} pendientes"}",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                },
                actions = {
                    IconButton(
                        onClick = { viewModel.toggleTheme(isDarkTheme) },
                        modifier = Modifier.size(40.dp)
                    ) {
                        Icon(
                            if (isDarkTheme) Icons.Default.LightMode else Icons.Default.DarkMode,
                            contentDescription = if (isDarkTheme) "Usar modo claro" else "Usar modo oscuro"
                        )
                    }
                    IconButton(onClick = viewModel::syncCatalog, enabled = !viewModel.isSyncingCatalog) {
                        if (viewModel.isSyncingCatalog) {
                            CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
                        } else {
                            BadgedBox(badge = { if (unsyncedSales.isNotEmpty()) Badge { Text(unsyncedSales.size.toString()) } }) {
                                Icon(Icons.Default.Refresh, contentDescription = "Sincronizar")
                            }
                        }
                    }
                    IconButton(onClick = viewModel::logout) {
                        Icon(Icons.Default.ExitToApp, contentDescription = "Cerrar sesión")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface)
            )
        },
        bottomBar = {
            NavigationBar(
                modifier = Modifier.testTag("app_navigation_bar"),
                containerColor = MaterialTheme.colorScheme.surface,
                tonalElevation = 0.dp
            ) {
                destinations.forEachIndexed { index, destination ->
                    NavigationBarItem(
                        selected = activeTab == index,
                        onClick = { activeTab = index },
                        icon = { Icon(destination.icon, contentDescription = destination.label) },
                        label = { Text(destination.label) },
                        colors = NavigationBarItemDefaults.colors(
                            indicatorColor = MaterialTheme.colorScheme.primaryContainer,
                            selectedIconColor = MaterialTheme.colorScheme.primary,
                            selectedTextColor = MaterialTheme.colorScheme.primary
                        )
                    )
                }
            }
        }
    ) { innerPadding ->
        Box(Modifier.fillMaxSize().padding(innerPadding)) {
            when (activeTab) {
                0 -> SaleScreen(
                    viewModel = viewModel,
                    onNavigateToInventoryWithBarcode = {
                        productFormRequest++
                        activeTab = 1
                    }
                )
                1 -> InventoryScreen(
                    viewModel = viewModel,
                    openProductFormRequest = productFormRequest,
                    onProductFormRequestHandled = { productFormRequest = 0 }
                )
                2 -> ClientListScreen(viewModel)
            }
        }
    }
}
