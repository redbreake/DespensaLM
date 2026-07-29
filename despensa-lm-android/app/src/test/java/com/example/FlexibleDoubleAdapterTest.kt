package com.example

import com.example.data.remote.FlexibleDoubleAdapter
import com.squareup.moshi.Moshi
import org.junit.Assert.assertEquals
import org.junit.Test

class FlexibleDoubleAdapterTest {
    private val adapter = Moshi.Builder()
        .add(FlexibleDoubleAdapter())
        .build()
        .adapter(Double::class.java)

    @Test
    fun parsesNumbersAndNumericStrings() {
        assertEquals(3900.0, adapter.fromJson("3900.0")!!, 0.0)
        assertEquals(3900.0, adapter.fromJson("\"3900.00\"")!!, 0.0)
    }
}
