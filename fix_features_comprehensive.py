#!/usr/bin/env python3
"""Comprehensive fix for features.py syntax and indentation issues"""

import re


def fix_features_py():
    """Fix all syntax and indentation issues in features.py"""

    with open("src/api/features.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Fix 1: Remove the extra newline at line 202
    content = re.sub(
        r'\) -> Dict\[str, Any\]:\s*\n\s*"""', r') -> Dict[str, Any]:\n    """', content
    )

    # Fix 2: Fix indentation after docstring (lines 212+)
    # Replace 8 spaces with 4 spaces for code block
    lines = content.split("\n")
    fixed_lines = []

    for i, line in enumerate(lines):
        line_num = i + 1

        # Fix indentation in get_team_features function (lines 212-266)
        if line_num >= 212 and line_num <= 266:
            if line.startswith("        "):
                # Check if it's inside a code block (not docstring)
                if (
                    not line.strip().startswith('"""')
                    and not line.strip().startswith("# ")
                    and line.strip()
                ):
                    # Reduce indentation from 8 to 4 spaces
                    line = "    " + line.lstrip()

        # Fix broken dictionary structure starting at line 236
        if line_num == 236 and '"' in line and "entity_rows" in line:
            # Close the get_online_features call properly
            line = "            ],"
        elif line_num == 237 and line.strip().startswith('"team_info"'):
            # Add missing closing parenthesis and bracket
            line = "        )"
        elif line_num == 238 and '"' in line and "team_id" in line:
            # Add proper response_data structure
            line = ""
        elif line_num == 239 and '"' in line and "team_name" in line:
            line = "        response_data = {"
        elif line_num == 240 and '"' in line and "league_id" in line:
            line = '            "team_info": {'
        elif line_num == 241 and '"' in line and "founded_year" in line:
            line = '                "team_id": team.id,'
        elif line_num == 242 and '"' in line and "venue" in line:
            line = '                "team_name": team.name,'
        elif line_num == 243 and '"' in line and "calculation_date" in line:
            line = '                "league_id": int(team.league_id),'
        elif line_num == 244 and '"' in line and "features" in line:
            line = '                "founded_year": team.founded_year,'
        elif line_num == 245 and line.strip().startswith("team_features.to_dict"):
            line = '                "venue": getattr(team, "venue", None),'
        elif line_num == 246 and line.strip().startswith("}"):
            line = "            },"
        elif line_num == 247 and line.strip().startswith("#"):
            line = '            "calculation_date": calculation_date.isoformat(),'
        elif line_num == 248 and line.strip().startswith("if"):
            line = '            "features": ('
        elif line_num == 249 and line.strip().startswith("team_entity"):
            line = '                team_features.to_dict("records")[0] if not team_features.empty else {}'
        elif line_num == 250 and line.strip().startswith("all_features"):
            line = "            ),"
        elif line_num == 251 and line.strip().startswith("team_entity"):
            line = "        }"
        elif line_num == 252 and line.strip().startswith("all_features"):
            line = ""
        elif line_num == 253 and line.strip().startswith("except"):
            line = "        # 如果需要原始特征数据，直接计算"
        elif line_num == 254 and line.strip().startswith("response_data"):
            line = "        if include_raw:"
        elif line_num == 255 and line.strip().startswith("data"):
            line = "            try:"
        elif line_num == 256 and line.strip().startswith("raise"):
            line = "                team_entity = TeamEntity("
        elif line_num == 257 and line.strip().startswith("except"):
            line = "                    team_id=int(team.id),"
        elif line_num == 258 and line.strip().startswith("}"):
            line = "                    team_name=team.name,"
        elif line_num == 259 and line.strip().startswith("message"):
            line = "                    league_id=int(team.league_id),"
        elif line_num == 260 and line.strip().startswith("raise"):
            line = '                    home_venue=getattr(team, "venue", None),'
        elif line_num == 261 and line.strip():
            line = "                )"
        elif line_num == 262:
            line = ""
        elif line_num == 263:
            line = "                all_features = await feature_calculator.calculate_all_team_features("
        elif line_num == 264:
            line = "                    team_entity, calculation_date"
        elif line_num == 265:
            line = "                )"
        elif line_num == 266:
            line = (
                '                response_data["raw_features"] = all_features.to_dict()'
            )
        elif line_num == 267:
            line = "            except Exception as e:"
        elif line_num == 268:
            line = '                response_data["raw_features_error"] = {"error": str(e)}'
        elif line_num == 269:
            line = ""
        elif line_num == 270:
            line = '        return APIResponse.success(data=response_data, message=f"成功获取球队 {team.name} 的特征")'
        elif line_num == 271:
            line = ""
        elif line_num == 272:
            line = "    except Exception as e:"
        elif line_num == 273:
            line = '        raise HTTPException(status_code=500, detail=f"获取球队特征失败: {str(e)}")'

        # Fix calculate_match_features function (lines 269+)
        if line_num >= 274:
            # Fix function signature
            if "async def calculate_match_features(" in line and ")" not in line:
                line = line.rstrip() + "\n    match_id: int,"
            elif "force_recalculate: bool" in line and ")" not in line:
                line = (
                    line.rstrip()
                    + "\n    session: AsyncSession = Depends(get_async_session),"
                )
            elif line.strip() == "计算比赛特征":
                line = '    """'
            elif line.strip().startswith("force_recalculate:"):
                line = "    计算比赛特征"
            elif line.strip().startswith("APIResponse:"):
                line = ""
            elif line.strip().startswith("match_id:"):
                line = "    "
            elif (
                line.strip()
                and "#" not in line
                and '"""' not in line
                and not line.startswith("    ")
            ):
                line = "    " + line

        fixed_lines.append(line)

    content = "\n".join(fixed_lines)

    # Fix 3: Fix the rest of the broken functions
    # Fix calculate_match_features
    content = re.sub(
        r'@router\.post\(\s*"/calculate/\{match_id\}",.*?\)\s*async def calculate_match_features\(\s*force_recalculate: bool = Query\(.*?\),\s*计算比赛特征.*?APIResponse: 计算结果',
        '''@router.post(
    "/calculate/{match_id}",
    summary="计算比赛特征",
    description="实时计算指定比赛的所有特征并存储到特征存储",
)
async def calculate_match_features(
    match_id: int,
    force_recalculate: bool = Query(default=False, description="是否强制重新计算"),
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """
    计算比赛特征

    Args:
        match_id: 比赛ID
        force_recalculate: 是否强制重新计算
        session: 数据库会话

    Returns:
        APIResponse: 计算结果
    """''',
        content,
        flags=re.DOTALL,
    )

    # Fix calculate_team_features
    content = re.sub(
        r'"/calculate/teams/\{team_id\}",',
        """@router.get(
    "/calculate/teams/{team_id}",""",
        content,
    )

    # Fix batch_calculate_features
    content = re.sub(
        r'"/batch/calculate",',
        """@router.post(
    "/batch/calculate",""",
        content,
    )

    # Fix get_historical_features
    content = re.sub(
        r'"/historical/\{match_id\}",',
        """@router.get(
    "/historical/{match_id}",""",
        content,
    )

    # Fix health check
    content = re.sub(
        r'@router\.get\(str\("/health", None\),', '@router.get("/health",', content
    )

    # Write the fixed content
    with open("src/api/features.py", "w", encoding="utf-8") as f:
        f.write(content)

    print("Fixed features.py")


if __name__ == "__main__":
    fix_features_py()
