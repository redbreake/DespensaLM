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
        editor.putString("cookie_host", url.host)
        for (cookie in cookies) {
            if (cookie.name == "sessionid" || cookie.name == "csrftoken") {
                editor.putString(cookie.name, cookie.value)
                editor.putBoolean("${cookie.name}_secure", cookie.secure)
            }
        }
        editor.apply()
    }

    @Synchronized
    override fun loadForRequest(url: HttpUrl): List<Cookie> {
        val host = url.host
        val sessionId = prefs.getString("sessionid", null)
        val csrfToken = prefs.getString("csrftoken", null)
        val savedHost = prefs.getString("cookie_host", null)
        if (savedHost == null && (sessionId != null || csrfToken != null)) {
            prefs.edit().putString("cookie_host", host).apply()
        } else if (savedHost != host) {
            return emptyList()
        }

        val buildCookies = mutableListOf<Cookie>()

        if (sessionId != null && canSendCookie("sessionid", url)) {
            buildCookies.add(buildCookie("sessionid", sessionId, host, url))
        }
        if (csrfToken != null && canSendCookie("csrftoken", url)) {
            buildCookies.add(buildCookie("csrftoken", csrfToken, host, url))
        }
        return buildCookies
    }

    private fun canSendCookie(name: String, url: HttpUrl): Boolean {
        return !prefs.getBoolean("${name}_secure", false) || url.isHttps
    }

    private fun buildCookie(name: String, value: String, host: String, url: HttpUrl): Cookie {
        val builder = Cookie.Builder()
            .name(name)
            .value(value)
            .hostOnlyDomain(host)
            .path("/")
        if (prefs.getBoolean("${name}_secure", false) && url.isHttps) {
            builder.secure()
        }
        return builder.build()
    }

    fun getCsrfToken(): String? {
        return prefs.getString("csrftoken", null)
    }

    fun clearCookies() {
        prefs.edit().clear().apply()
    }
}
