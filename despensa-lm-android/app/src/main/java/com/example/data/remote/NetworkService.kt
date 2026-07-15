package com.example.data.remote

import android.content.Context
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import java.util.concurrent.TimeUnit

class NetworkService(context: Context) {
    private val prefs = context.getSharedPreferences("despensa_lm_network", Context.MODE_PRIVATE)
    
    val cookieJar = SessionCookieJar(context)
    
    fun getSavedBaseUrl(): String {
        val saved = prefs.getString("base_url", "https://despensalm.pythonanywhere.com/") ?: "https://despensalm.pythonanywhere.com/"
        if (saved.contains("ais-pre-") || saved.contains("ais-dev-") || saved.contains("127.0.0.1") || saved.contains("localhost")) {
            return "https://despensalm.pythonanywhere.com/"
        }
        return saved
    }

    fun saveBaseUrl(url: String) {
        val sanitized = if (url.endsWith("/")) url else "$url/"
        prefs.edit().putString("base_url", sanitized).apply()
        rebuildRetrofit(sanitized)
    }

    private val moshi = Moshi.Builder()
        .add(FlexibleDoubleAdapter())
        .add(KotlinJsonAdapterFactory())
        .build()

    @Volatile
    private var apiService: ApiService? = null

    init {
        rebuildRetrofit(getSavedBaseUrl())
    }

    @Synchronized
    private fun rebuildRetrofit(baseUrl: String) {
        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BASIC
        }

        val headerInterceptor = Interceptor { chain ->
            val original = chain.request()
            val requestBuilder = original.newBuilder()
                .header("Accept", "application/json")
                
            // If CSRF token is available, inject it
            cookieJar.getCsrfToken()?.let { csrf ->
                requestBuilder.header("X-CSRFToken", csrf)
                requestBuilder.header("Referer", baseUrl)
            }
            
            chain.proceed(requestBuilder.build())
        }

        val client = OkHttpClient.Builder()
            .cookieJar(cookieJar)
            .addInterceptor(headerInterceptor)
            .addInterceptor(logging)
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(15, TimeUnit.SECONDS)
            .build()

        try {
            val retrofit = Retrofit.Builder()
                .baseUrl(baseUrl)
                .client(client)
                .addConverterFactory(MoshiConverterFactory.create(moshi))
                .build()
            
            apiService = retrofit.create(ApiService::class.java)
        } catch (e: Exception) {
            e.printStackTrace()
            apiService = null
        }
    }

    fun getApi(): ApiService? {
        if (apiService == null) {
            rebuildRetrofit(getSavedBaseUrl())
        }
        return apiService
    }
}
