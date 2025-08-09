#ifndef ATTENDANCE_H
#define ATTENDANCE_H

#ifdef __cplusplus

extern "C"
{
    #endif

// Return codes for mark_attendance:
//  0 = success (new mark)
//  1 = already marked today
// -1 = error (I/O etc)

int mark_attendance(const char *data_dir, const char *name);

// rotate today's CSV into archive_path (archive_path must include filename).
// Return 0 on success, -1 on error.

int rotate_today_csv(const char *data_dir, const char *archive_path);

#ifdef __cplusplus

}
#endif

#endif