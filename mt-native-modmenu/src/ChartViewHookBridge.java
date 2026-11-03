package mt.nativeaddon;

import android.app.Activity;
import android.os.Looper;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;

/**
 * Controlled, opt-in chart-view attachment bridge.
 * A verified integration caller supplies the chart view and chart identity.
 * This does not scan private views, patch DEX offsets or intercept trade calls.
 */
public final class ChartViewHookBridge {
    private final Activity activity;
    private final Mt5ChartMenuHost host;
    private FrameLayout overlayParent;
    private View chartView;
    private int chartId = -1;
    private long revision = -1L;

    public ChartViewHookBridge(Activity activity, Mt5ResearchMenu.Listener listener) {
        if (activity == null || listener == null) throw new IllegalArgumentException("activity/listener");
        this.activity = activity;
        this.host = new Mt5ChartMenuHost(activity, listener);
    }

    /** Call on UI thread after a verified chart view has entered the hierarchy. */
    public void onChartAttached(View verifiedChartView, int id, long viewportRevision) {
        requireMainThread();
        if (verifiedChartView == null || id < 0 || viewportRevision < 0)
            throw new IllegalArgumentException("invalid chart identity");
        if (verifiedChartView.getWindowToken() == null)
            throw new IllegalStateException("chart is not attached");
        if (!(verifiedChartView.getParent() instanceof FrameLayout))
            throw new IllegalStateException("chart parent must be FrameLayout");
        FrameLayout parent = (FrameLayout) verifiedChartView.getParent();
        if (parent.getContext() != activity)
            throw new IllegalStateException("chart belongs to another context");
        if (chartView == verifiedChartView && chartId == id
                && revision == viewportRevision && host.isAttached()) return;
        detach();
        chartView = verifiedChartView;
        chartId = id;
        revision = viewportRevision;
        overlayParent = parent;
        host.attach(parent, id, viewportRevision);
    }

    public void onChartChanged(int id, long viewportRevision) {
        requireMainThread();
        if (id != chartId || viewportRevision != revision) detach();
    }

    public void onChartDetached(View detachedView) {
        requireMainThread();
        if (chartView == detachedView) detach();
    }

    public void detach() {
        requireMainThread();
        host.detach();
        overlayParent = null;
        chartView = null;
        chartId = -1;
        revision = -1L;
    }

    public boolean isAttached() { return host.isAttached(); }

    private static void requireMainThread() {
        if (Looper.myLooper() != Looper.getMainLooper())
            throw new IllegalStateException("UI thread required");
    }
}
