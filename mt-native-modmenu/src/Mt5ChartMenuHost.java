package mt.nativeaddon;

import android.content.Context;
import android.view.View;
import android.widget.FrameLayout;

/**
 * Controlled in-app chart attachment boundary. The host must explicitly supply
 * a verified chart parent; this class does not discover or hook MT5 internals.
 * No native offsets, trading calls, permissions, or external overlay windows.
 */
public final class Mt5ChartMenuHost {
    private final Mt5ResearchMenu menu;
    private FrameLayout chartParent;
    private int chartId = -1;
    private long viewportRevision = -1L;

    public Mt5ChartMenuHost(Context context, Mt5ResearchMenu.Listener listener) {
        menu = new Mt5ResearchMenu(context, listener);
    }

    /** Call only on the Android main thread after the chart parent is attached. */
    public void attach(FrameLayout verifiedChartParent, int id, long revision) {
        if (verifiedChartParent == null || id < 0 || revision < 0)
            throw new IllegalArgumentException("verified chart identity required");
        if (verifiedChartParent.getWindowToken() == null)
            throw new IllegalStateException("chart parent is not attached to a window");
        detach();
        chartParent = verifiedChartParent;
        chartId = id;
        viewportRevision = revision;
        menu.attach(verifiedChartParent);
    }

    /** Fail closed when chart identity or viewport changes. */
    public void onChartChanged(int id, long revision) {
        if (id != chartId || revision != viewportRevision) detach();
    }

    public boolean isAttached() { return chartParent != null; }

    public void detach() {
        menu.detach();
        chartParent = null;
        chartId = -1;
        viewportRevision = -1L;
    }
}
