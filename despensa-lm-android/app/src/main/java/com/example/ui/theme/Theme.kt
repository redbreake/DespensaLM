package com.example.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColorScheme = lightColorScheme(
    primary = Evergreen,
    onPrimary = androidx.compose.ui.graphics.Color.White,
    primaryContainer = Mint,
    onPrimaryContainer = EvergreenDark,
    secondary = Coral,
    onSecondary = androidx.compose.ui.graphics.Color.White,
    secondaryContainer = CoralSoft,
    onSecondaryContainer = androidx.compose.ui.graphics.Color(0xFF5C190F),
    background = Canvas,
    onBackground = Ink,
    surface = androidx.compose.ui.graphics.Color.White,
    onSurface = Ink,
    surfaceVariant = SurfaceSoft,
    onSurfaceVariant = InkMuted,
    outline = Color(0xFF74817A),
    outlineVariant = Line,
    error = Color(0xFFB3261E),
    errorContainer = Color(0xFFFFDAD6)
)

private val DarkColorScheme = darkColorScheme(
    primary = Color(0xFF71D5AA),
    onPrimary = Color(0xFF003826),
    primaryContainer = Color(0xFF07513A),
    onPrimaryContainer = Color(0xFFA4F2CF),
    secondary = Color(0xFFFFB4A8),
    onSecondary = Color(0xFF680006),
    secondaryContainer = Color(0xFF8E241E),
    onSecondaryContainer = Color(0xFFFFDAD4),
    background = NightCanvas,
    onBackground = Color(0xFFE2EAE5),
    surface = NightSurface,
    onSurface = Color(0xFFE2EAE5),
    surfaceVariant = NightSurfaceSoft,
    onSurfaceVariant = Color(0xFFBBC8C0),
    outline = Color(0xFF89978F),
    outlineVariant = NightLine
)

@Composable
fun MyApplicationTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme,
        typography = Typography,
        content = content
    )
}
