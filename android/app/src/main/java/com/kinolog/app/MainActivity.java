package com.kinolog.app;

import android.app.Activity;
import android.content.res.AssetManager;
import android.os.Bundle;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebChromeClient;
import android.widget.ProgressBar;
import android.widget.LinearLayout;
import android.graphics.Color;
import android.util.Log;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

public class MainActivity extends Activity {
    private static final String TAG = "KinoLog";
    private static final int PORT = 8000;
    private static final String URL = "http://127.0.0.1:" + PORT;
    
    private WebView webView;
    private ProgressBar progressBar;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(
            WindowManager.LayoutParams.FLAG_FULLSCREEN,
            WindowManager.LayoutParams.FLAG_FULLSCREEN
        );
        
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setBackgroundColor(Color.BLACK);
        
        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setIndeterminate(true);
        progressBar.setVisibility(android.view.View.VISIBLE);
        layout.addView(progressBar, new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        ));
        
        webView = new WebView(this);
        webView.setBackgroundColor(Color.BLACK);
        layout.addView(webView, new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.MATCH_PARENT
        ));
        
        setContentView(layout);
        
        setupWebView();
        
        new Thread(() -> {
            try {
                extractAssets();
                startPythonServer();
            } catch (Exception e) {
                Log.e(TAG, "Init error", e);
            }
        }).start();
    }

    private void extractAssets() {
        File filesDir = getFilesDir();
        AssetManager assetManager = getAssets();
        
        try {
            copyAssetFolder(assetManager, "templates", new File(filesDir, "templates"));
            copyAssetFolder(assetManager, "static", new File(filesDir, "static"));
            Log.d(TAG, "Assets extracted to " + filesDir.getAbsolutePath());
        } catch (IOException e) {
            Log.e(TAG, "Error extracting assets", e);
        }
        
        File configDir = new File(filesDir, "config");
        if (!configDir.exists()) {
            configDir.mkdirs();
        }
        
        File envFile = new File(configDir, ".env");
        if (!envFile.exists()) {
            try {
                InputStream in = assetManager.open(".env");
                FileOutputStream out = new FileOutputStream(envFile);
                byte[] buffer = new byte[1024];
                int read;
                while ((read = in.read(buffer)) != -1) {
                    out.write(buffer, 0, read);
                }
                out.close();
                in.close();
                Log.d(TAG, "Created .env in config folder");
            } catch (IOException e) {
                try {
                    FileOutputStream out = new FileOutputStream(envFile);
                    out.write("OMDB_API_KEY=\nDROPBOX_APP_KEY=\nDROPBOX_APP_SECRET=\nDROPBOX_REDIRECT_URI=http://localhost:8000/api/dropbox/callback\n".getBytes());
                    out.close();
                    Log.d(TAG, "Created empty .env in config folder");
                } catch (IOException ex) {
                    Log.e(TAG, "Error creating .env", ex);
                }
            }
        }
    }
    
    private void copyAssetFolder(AssetManager assetManager, String srcDir, File dstDir) throws IOException {
        String[] files = assetManager.list(srcDir);
        if (files == null || files.length == 0) {
            return;
        }
        
        if (!dstDir.exists()) {
            dstDir.mkdirs();
        }
        
        for (String file : files) {
            String srcPath = srcDir + "/" + file;
            File dstFile = new File(dstDir, file);
            
            String[] subFiles = assetManager.list(srcPath);
            if (subFiles != null && subFiles.length > 0) {
                copyAssetFolder(assetManager, srcPath, dstFile);
            } else {
                copyAssetFile(assetManager, srcPath, dstFile);
            }
        }
    }
    
    private void copyAssetFile(AssetManager assetManager, String srcFile, File dstFile) throws IOException {
        if (dstFile.exists()) {
            return;
        }
        
        try (InputStream in = assetManager.open(srcFile);
             OutputStream out = new FileOutputStream(dstFile)) {
            byte[] buffer = new byte[1024];
            int read;
            while ((read = in.read(buffer)) != -1) {
                out.write(buffer, 0, read);
            }
        }
    }

    private void setupWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setSupportZoom(false);
        
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                view.loadUrl(url);
                return true;
            }
            
            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                progressBar.setVisibility(android.view.View.GONE);
            }
        });
        
        webView.setWebChromeClient(new WebChromeClient());
    }

    private void startPythonServer() {
        try {
            if (!Python.isStarted()) {
                Python.start(new AndroidPlatform(this));
            }
            
            Python python = Python.getInstance();
            
            String appPath = getFilesDir().getAbsolutePath();
            String dbPath = appPath + "/kinopoisk.db";
            
            PyObject module = python.getModule("server");
            module.callAttr("start_server", PORT, appPath, dbPath);
            
            new android.os.Handler(android.os.Looper.getMainLooper()).post(() -> {
                waitForServerAndLoad();
            });
            
        } catch (Exception e) {
            Log.e(TAG, "Python server error", e);
        }
    }

    private void waitForServerAndLoad() {
        new Thread(() -> {
            int attempts = 0;
            while (attempts < 60) {
                try {
                    java.net.URL url = new java.net.URL(URL);
                    java.net.HttpURLConnection connection = (java.net.HttpURLConnection) url.openConnection();
                    connection.setConnectTimeout(1000);
                    connection.setReadTimeout(1000);
                    int responseCode = connection.getResponseCode();
                    connection.disconnect();
                    
                    if (responseCode == 200) {
                        new android.os.Handler(android.os.Looper.getMainLooper()).post(() -> {
                            webView.loadUrl(URL);
                        });
                        return;
                    }
                } catch (Exception e) {
                    // Server not ready
                }
                attempts++;
                try {
                    Thread.sleep(500);
                } catch (InterruptedException e) {
                    break;
                }
            }
            
            new android.os.Handler(android.os.Looper.getMainLooper()).post(() -> {
                progressBar.setVisibility(android.view.View.GONE);
                webView.loadUrl(URL);
            });
        }).start();
    }

    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.destroy();
        }
        super.onDestroy();
    }
}
