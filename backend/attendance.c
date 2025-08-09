#define _XOPEN_SOURCE 700
#include "attendance.h"

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>


static void ensure_dir(const char *path)
{
    struct stat st;
    if(stat(path, &st) == -1)
    {
        mkdir(path, 0755);
    }
}


static void today_filename(const char *dir, char *out, size_t outsz)
{
    time_t t = time(NULL);
    struct tm tm = *localtime(&t);
    char buf[64];

    strftime(buf, sizeof(buf), "attendance_%Y-%m-%d.csv", &tm);
    snprintf(out, outsz, "%s%s", dir, buf);
}

static void timestamp_now(char *out, size_t outsz)
{
    time_t t = time(NULL);
    struct tm tm = *localtime(&t);
    strftime(out, outsz, "%Y-%m-%d %H:%M:%S", &tm);
}

int mark_attendance(const char *data_dir, const char *name)
{
    if(!data_dir || !name)
    {
        return -1;
    }

    ensure_dir(data_dir);
    char file_path[512];
    today_filename(data_dir, file_path, sizeof(file_path));

    // open/create file, check duplicate
    FILE *f = fopen(file_path, "a+");
    if(!f)
    {
        return -1;
    }

    // check if name already exists
    rewind(f);
    char *line = NULL;
    size_t len = 0;
    ssize_t r;
    while((r = getline(&line, &len, f)) != -1)
    {
        char *comma = strchr(line, ',');
        if(!comma)
        {
            continue;
        }
        *comma = '\0';
        char *existing = line;
        while(*existing && (*existing == ' ' || *existing == '\t' || *existing == '\r' || *existing == '\n'))
        {
            existing++;
        }

        if(strcmp(existing, name) == 0)
        {
            free(line);
            fclose(f);
            return -1;
        }
    }

    free(line);


    char ts[64];
    timestamp_now(ts, sizeof(ts));
    if(fprintf(f, "%s, %s\n", name, ts) < 0)
    {
        fclose(f);
        return -1;
    }
    fflush(f);
    fclose(f);
    return 0;
}

int rotate_today_csv(const char *data_dir, const char *archive_path)
{
    if(!data_dir || !archive_path)
    {
        return -1; 
    }

    char file_path[512];
    today_filename(data_dir, file_path, sizeof(file_path));

    if(access(file_path, F_OK) != 0)
    {
        FILE *af = fopen(archive_path, "w");
        if(!af)
        {
            return -1;
        }
        fclose(af);
        return 0;
    }

    if(rename(file_path, archive_path) != 0)
    {
        FILE *src = fopen(file_path, "r");
        FILE *dst = fopen(archive_path, "w");

        if(!src || !dst)
        {
            if(src)
            {
                fclose(src);
            }
            if(dst)
            {
                fclose(dst);
            }
            return -1;
        }

        char buf[4096];
        size_t n;
        while((n = fread(buf, 1, sizeof(buf), src)) > 0)
        {
            if(fwrite (buf, 1, n, dst) != n)
            {
                fclose(src);
                fclose(dst);
                return -1;
            }
        }
        fclose(src);
        fclose(dst);

        FILE *orig = fopen(file_path, "w");
        if(orig)
        {
            fclose(orig);
        }
    }
    return 0;
}
