package com.example

import android.app.Application
import com.example.data.local.AppDatabase
import com.example.data.remote.NetworkService
import com.example.data.repository.ClientRepository
import com.example.data.repository.ProductRepository
import com.example.data.repository.SalesRepository

class DespensaLMApplication : Application() {
    lateinit var database: AppDatabase
    lateinit var networkService: NetworkService
    lateinit var productRepository: ProductRepository
    lateinit var clientRepository: ClientRepository
    lateinit var salesRepository: SalesRepository

    override fun onCreate() {
        super.onCreate()
        database = AppDatabase.getDatabase(this)
        networkService = NetworkService(this)
        productRepository = ProductRepository(database.productDao(), networkService)
        clientRepository = ClientRepository(database.clientDao(), networkService)
        salesRepository = SalesRepository(database.offlineSaleDao(), database.productDao(), networkService)
    }
}
