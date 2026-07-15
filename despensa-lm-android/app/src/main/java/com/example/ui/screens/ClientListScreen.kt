package com.example.ui.screens

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.example.data.local.CachedClient
import com.example.data.remote.AccountMovementResponse
import com.example.data.remote.ClientDetailResponse
import com.example.data.remote.ClientResponse
import com.example.ui.AppViewModel
import com.example.ui.components.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ClientListScreen(viewModel: AppViewModel, modifier: Modifier = Modifier) {
    var searchQuery by remember { mutableStateOf("") }
    var activeClient by remember { mutableStateOf<CachedClient?>(null) }
    var editingClient by remember { mutableStateOf<ClientResponse?>(null) }
    var showEditor by remember { mutableStateOf(false) }
    var movementClient by remember { mutableStateOf<CachedClient?>(null) }
    var movementType by remember { mutableStateOf("PAGO") }
    val allClients by viewModel.allClients.collectAsState()

    val filteredClients = remember(searchQuery, allClients) {
        (if (searchQuery.isBlank()) allClients else allClients.filter {
            it.nombre.contains(searchQuery, true) || it.telefono.contains(searchQuery, true)
        }).sortedWith(compareByDescending<CachedClient> { it.saldo_actual > 0 }.thenBy { it.nombre })
    }
    val debtors = allClients.count { it.saldo_actual > 0 }
    val totalDebt = allClients.sumOf { it.saldo_actual.coerceAtLeast(0.0) }

    activeClient?.let { client ->
        LaunchedEffect(client.id) { viewModel.loadClientDetail(client.id) }
        ClientDetailSheet(
            client = client,
            detail = viewModel.clientDetail,
            loading = viewModel.clientActionLoading,
            error = viewModel.clientActionError,
            onDismiss = {
                activeClient = null
                viewModel.clearClientActionState()
            },
            onEdit = {
                editingClient = viewModel.clientDetail?.cliente ?: client.toResponse()
                activeClient = null
                showEditor = true
            },
            onMovement = { type ->
                movementClient = client
                movementType = type
                activeClient = null
            }
        )
    }

    if (showEditor) {
        ClientEditorSheet(
            viewModel = viewModel,
            client = editingClient,
            onDismiss = {
                showEditor = false
                editingClient = null
                viewModel.clearClientActionState()
            }
        )
    }

    movementClient?.let { client ->
        ClientMovementSheet(
            viewModel = viewModel,
            client = client,
            type = movementType,
            onDismiss = {
                movementClient = null
                viewModel.clearClientActionState()
            }
        )
    }

    Column(modifier.fillMaxSize()) {
        Column(Modifier.padding(horizontal = 16.dp, vertical = 14.dp)) {
            ScreenIntro("Clientes", "Saldos y cuentas corrientes")
            Spacer(Modifier.height(14.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                MetricTile("Registrados", allClients.size.toString(), Modifier.weight(1f))
                MetricTile("Con deuda", debtors.toString(), Modifier.weight(1f), emphasized = debtors > 0)
                MetricTile("Total fiado", money(totalDebt), Modifier.weight(1.35f), emphasized = totalDebt > 0)
            }
            Spacer(Modifier.height(14.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                AppSearchField(
                    searchQuery,
                    { searchQuery = it },
                    "Nombre o teléfono",
                    Modifier.weight(1f).testTag("client_search_input")
                )
                Button(
                    onClick = {
                        viewModel.clearClientActionState()
                        editingClient = null
                        showEditor = true
                    },
                    modifier = Modifier.height(56.dp),
                    shape = RoundedCornerShape(8.dp),
                    contentPadding = PaddingValues(horizontal = 14.dp)
                ) {
                    Icon(Icons.Default.PersonAdd, contentDescription = null)
                    Spacer(Modifier.width(4.dp))
                    Text("Nuevo")
                }
            }
        }
        HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 10.dp),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text("${filteredClients.size} clientes", style = MaterialTheme.typography.labelLarge)
            if (debtors > 0) Text("Deudas primero", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.secondary)
        }

        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
            contentPadding = PaddingValues(bottom = 16.dp)
        ) {
            if (filteredClients.isEmpty()) {
                item {
                    EmptyState(Icons.Default.Person, "Sin resultados", "No hay clientes que coincidan con la búsqueda.", Modifier.fillParentMaxWidth().padding(top = 48.dp))
                }
            } else {
                items(filteredClients, key = { it.id }) { client ->
                    ClientRow(client) {
                        viewModel.clearClientActionState()
                        activeClient = client
                    }
                }
            }
        }
    }
}

@Composable
private fun ClientRow(client: CachedClient, onClick: () -> Unit) {
    val hasDebt = client.saldo_actual > 0
    Surface(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        shape = RoundedCornerShape(8.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, if (hasDebt) MaterialTheme.colorScheme.secondary.copy(alpha = .45f) else MaterialTheme.colorScheme.outlineVariant)
    ) {
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Surface(
                modifier = Modifier.size(42.dp),
                shape = RoundedCornerShape(8.dp),
                color = if (hasDebt) MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.primaryContainer
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Text(client.nombre.trim().take(1).uppercase(), style = MaterialTheme.typography.titleMedium)
                }
            }
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(client.nombre, style = MaterialTheme.typography.titleMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                if (client.telefono.isNotBlank()) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Default.Phone, contentDescription = null, modifier = Modifier.size(13.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                        Spacer(Modifier.width(4.dp))
                        Text(client.telefono, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                } else {
                    Text("Sin teléfono", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(money(client.saldo_actual), style = MaterialTheme.typography.titleMedium, color = if (hasDebt) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.primary)
                StatusPill(if (hasDebt) "Debe" else "Al día", positive = !hasDebt)
            }
            Spacer(Modifier.width(4.dp))
            Icon(Icons.Default.ChevronRight, contentDescription = "Abrir cuenta", tint = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ClientDetailSheet(
    client: CachedClient,
    detail: ClientDetailResponse?,
    loading: Boolean,
    error: String?,
    onDismiss: () -> Unit,
    onEdit: () -> Unit,
    onMovement: (String) -> Unit
) {
    val context = LocalContext.current
    val remoteClient = detail?.cliente
    val balance = remoteClient?.saldoActual ?: client.saldo_actual

    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(Modifier.fillMaxWidth().padding(horizontal = 20.dp).padding(bottom = 28.dp)) {
            Row(verticalAlignment = Alignment.Top) {
                Column(Modifier.weight(1f)) {
                    Text(remoteClient?.nombre ?: client.nombre, style = MaterialTheme.typography.headlineSmall)
                    Text(
                        (remoteClient?.telefono ?: client.telefono).ifBlank { "Sin teléfono" },
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                if ((remoteClient?.telefono ?: client.telefono).isNotBlank()) {
                    IconButton(onClick = {
                        val phone = remoteClient?.telefono ?: client.telefono
                        context.startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:$phone")))
                    }) { Icon(Icons.Default.Phone, contentDescription = "Llamar") }
                }
                IconButton(onClick = onEdit) { Icon(Icons.Default.Edit, contentDescription = "Editar cliente") }
            }
            Spacer(Modifier.height(14.dp))
            Surface(shape = RoundedCornerShape(8.dp), color = MaterialTheme.colorScheme.surfaceVariant) {
                Row(Modifier.fillMaxWidth().padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f)) {
                        Text("Saldo pendiente", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text(money(balance), style = MaterialTheme.typography.headlineMedium, color = if (balance > 0) MaterialTheme.colorScheme.secondary else MaterialTheme.colorScheme.primary)
                    }
                    StatusPill(if (balance > 0) "Debe" else "Al día", positive = balance <= 0)
                }
            }
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Button(
                    onClick = { onMovement("PAGO") },
                    enabled = balance > 0,
                    modifier = Modifier.weight(1f).height(52.dp),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Icon(Icons.Default.Payments, contentDescription = null)
                    Spacer(Modifier.width(6.dp))
                    Text("Registrar pago")
                }
                OutlinedButton(
                    onClick = { onMovement("DEUDA") },
                    modifier = Modifier.weight(1f).height(52.dp),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Icon(Icons.Default.Add, contentDescription = null)
                    Spacer(Modifier.width(6.dp))
                    Text("Agregar deuda")
                }
            }
            Spacer(Modifier.height(18.dp))
            Text("Movimientos", style = MaterialTheme.typography.titleMedium)
            Spacer(Modifier.height(8.dp))
            when {
                loading && detail == null -> Box(Modifier.fillMaxWidth().height(160.dp), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
                error != null -> Text(error, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodyMedium)
                detail?.movimientos.isNullOrEmpty() -> Text("Todavía no hay movimientos en esta cuenta.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                else -> LazyColumn(Modifier.fillMaxWidth().heightIn(max = 320.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    items(detail!!.movimientos, key = { it.id }) { MovementRow(it) }
                }
            }
        }
    }
}

@Composable
private fun MovementRow(movement: AccountMovementResponse) {
    val isPayment = movement.tipoMovimiento == "PAGO"
    Surface(shape = RoundedCornerShape(8.dp), color = MaterialTheme.colorScheme.surfaceVariant) {
        Row(Modifier.fillMaxWidth().padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(
                if (isPayment) Icons.Default.SouthWest else Icons.Default.NorthEast,
                contentDescription = null,
                tint = if (isPayment) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.secondary
            )
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)) {
                Text(if (isPayment) "Pago recibido" else "Deuda", style = MaterialTheme.typography.titleSmall)
                Text(
                    movement.descripcion.ifBlank { formatMovementDate(movement.fecha) },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
            Text(
                (if (isPayment) "−" else "+") + money(movement.monto),
                style = MaterialTheme.typography.titleSmall,
                color = if (isPayment) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.secondary
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ClientEditorSheet(viewModel: AppViewModel, client: ClientResponse?, onDismiss: () -> Unit) {
    var name by remember(client?.id) { mutableStateOf(client?.nombre.orEmpty()) }
    var phone by remember(client?.id) { mutableStateOf(client?.telefono.orEmpty()) }
    var notes by remember(client?.id) { mutableStateOf(client?.notas.orEmpty()) }

    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(
            Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).imePadding().padding(horizontal = 20.dp).padding(bottom = 28.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(if (client == null) "Nuevo cliente" else "Editar cliente", style = MaterialTheme.typography.headlineSmall)
            OutlinedTextField(name, { name = it }, Modifier.fillMaxWidth(), label = { Text("Nombre") }, singleLine = true, shape = RoundedCornerShape(8.dp))
            OutlinedTextField(
                phone,
                { phone = it },
                Modifier.fillMaxWidth(),
                label = { Text("Teléfono") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                singleLine = true,
                shape = RoundedCornerShape(8.dp)
            )
            OutlinedTextField(notes, { notes = it }, Modifier.fillMaxWidth(), label = { Text("Notas") }, minLines = 2, maxLines = 4, shape = RoundedCornerShape(8.dp))
            viewModel.clientActionError?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedButton(onClick = onDismiss, Modifier.weight(1f).height(52.dp), shape = RoundedCornerShape(8.dp)) { Text("Cancelar") }
                Button(
                    onClick = { viewModel.saveClient(client?.id, name, phone, notes, onDismiss) },
                    enabled = !viewModel.clientActionLoading,
                    modifier = Modifier.weight(1.4f).height(52.dp),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    if (viewModel.clientActionLoading) CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp, color = MaterialTheme.colorScheme.onPrimary)
                    else Text("Guardar cliente", fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ClientMovementSheet(
    viewModel: AppViewModel,
    client: CachedClient,
    type: String,
    onDismiss: () -> Unit
) {
    var amount by remember(client.id, type) { mutableStateOf("") }
    var description by remember(client.id, type) { mutableStateOf("") }
    val isPayment = type == "PAGO"

    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(
            Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).imePadding().padding(horizontal = 20.dp).padding(bottom = 28.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(if (isPayment) "Registrar pago" else "Agregar deuda", style = MaterialTheme.typography.headlineSmall)
            Text(client.nombre, style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            OutlinedTextField(
                amount,
                { amount = it },
                Modifier.fillMaxWidth().testTag("client_movement_amount"),
                label = { Text("Monto") },
                prefix = { Text("$ ") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                singleLine = true,
                shape = RoundedCornerShape(8.dp)
            )
            OutlinedTextField(
                description,
                { description = it },
                Modifier.fillMaxWidth(),
                label = { Text("Detalle opcional") },
                minLines = 2,
                maxLines = 3,
                shape = RoundedCornerShape(8.dp)
            )
            viewModel.clientActionError?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
            Button(
                onClick = { viewModel.addClientMovement(client.id, type, amount, description, onDismiss) },
                enabled = !viewModel.clientActionLoading,
                modifier = Modifier.fillMaxWidth().height(54.dp),
                shape = RoundedCornerShape(8.dp),
                colors = if (isPayment) ButtonDefaults.buttonColors() else ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.secondary)
            ) {
                if (viewModel.clientActionLoading) CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp, color = MaterialTheme.colorScheme.onPrimary)
                else Text(if (isPayment) "Confirmar pago" else "Confirmar deuda", fontWeight = FontWeight.Bold)
            }
        }
    }
}

private fun CachedClient.toResponse() = ClientResponse(id, nombre, telefono, "", saldo_actual)

private fun formatMovementDate(value: String): String {
    val parts = value.take(10).split('-')
    return if (parts.size == 3) "${parts[2]}/${parts[1]}/${parts[0]}" else value
}
