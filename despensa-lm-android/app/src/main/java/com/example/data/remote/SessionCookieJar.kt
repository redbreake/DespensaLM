package com.example.data.remote

import android.content.Context
import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.HttpUrl

class SessionCookieJar(context: Context) : CookieJar {
    private val prefs = context.getSharedPreferences("despensa_lm_cookies", Context.MODE_PRIVATE)

    @Synchronized
    override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
        val editor = prefs.edit()
        for (cookie in cookies) {
            if (cookie.name == "sessionid" || cookie.name == "csrftoken") {
                editor.putString(cookie.name, cookie.value)
            }
        }
        editor.apply()
    }

    @Synchronized
    override fun loadForRequest(url: HttpUrl): List<Cookie> {
        val host = url.host
        val buildCookies = mutableListOf<Cookie>()
        
        val sessionId = prefs.getString("sessionid", null)
        val csrfToken = prefs.getString("csrftoken", null)
        
        if (sessionId != null) {
            buildCookies.add(
                Cookie.Builder()
                    .name("sessionid")
                    .value(sessionId)
                    .domain(host)
                    .path("/")
                    .build()
            )
        }
        if (csrfToken != null) {
            buildCookies.add(
                Cookie.Builder()
                    .name("csrftoken")
                    .value(csrfToken)
                    .domain(host)
                    .path("/")
                    .build()
            )
        }
        return buildCookies
    }

    fun getCsrfToken(): String? {
        return prefs.getString("csrftoken", null)
    }

    fun clearCookies() {
        prefs.edit().clear().apply()
    }
}
